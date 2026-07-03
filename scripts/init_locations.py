"""初始化省市区地区数据：调用和风地区搜索 API，构建 省/市/区 三级层级"""
import asyncio
import httpx
import jwt
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete

from src.config.settings import settings
from src.modules.location.location_model import LocationDb, LocationLevel


# 全国 34 个省级单位
PROVINCES = [
    "北京", "上海", "天津", "重庆",  # 直辖市
    "河北", "山西", "内蒙古",  # 华北
    "辽宁", "吉林", "黑龙江",  # 东北
    "江苏", "浙江", "安徽", "福建", "江西", "山东",  # 华东
    "河南", "湖北", "湖南",  # 华中
    "广东", "广西", "海南",  # 华南
    "四川", "贵州", "云南", "西藏",  # 西南
    "陕西", "甘肃", "青海", "宁夏", "新疆",  # 西北
]


def get_qweather_token():
    """生成和风 JWT token"""
    path = settings.he_feng_bem
    now = int(time.time())

    with open(path, "r") as f:
        private_key = f.read()

    payload = {
        "sub": settings.HE_FENG_SID,
        "iat": now - 30,
        "exp": now + 900,
    }

    headers = {
        "alg": settings.HE_FENG_ALGORITHM,
        "kid": settings.HE_FENG_KID,
    }

    token = jwt.encode(
        payload, private_key, algorithm=settings.HE_FENG_ALGORITHM, headers=headers
    )
    return f"Bearer {token}"


async def fetch_locations_from_qweather():
    """调用和风地区搜索 API，按省拉取地区，保留 adm1(省)/adm2(市) 用于构建层级"""
    token = get_qweather_token()
    api_host = settings.he_feng_api_prefix  # 你的专属 host
    raw = []

    async with httpx.AsyncClient() as client:
        for province in PROVINCES:
            # number=20 为和风单次返回上限，尽量多拉一些下级地区
            url = f"{api_host}/v2/city/lookup?location={province}&number=20"
            try:
                resp = await client.get(url, headers={"Authorization": token})
                data = resp.json()

                if data.get("code") == "200" and data.get("location"):
                    count = 0
                    for city in data["location"]:
                        code = city["id"]
                        # 只保留中国地区编码（9位纯数字）
                        if len(code) == 9 and code.isdigit():
                            raw.append({
                                "code": code,
                                "name": city["name"],
                                "adm1": city.get("adm1") or province,  # 省
                                "adm2": city.get("adm2") or city["name"],  # 市
                            })
                            count += 1
                    print(f"✅ {province}: 拉取 {count} 个中国地区")
                else:
                    print(f"⚠️  {province}: {data.get('code', 'unknown')} - {data.get('userInfo', {}).get('text', 'error')}")
            except Exception as e:
                print(f"❌ {province}: 请求失败 - {e}")

    return raw


def build_hierarchy(raw):
    """把和风返回的叶子地区整理成 省/市/区 三级，并生成 parent_code。

    - 区/县：使用和风 9 位 id 作为 code（真实唯一）
    - 省 / 市：和风未返回其编码，用 P 前缀生成稳定的合成 code
    返回按 省→市→区 顺序排列的 (code, name, level, parent_code) 列表，保证父先于子插入。
    """
    provinces = {}  # 省名 -> code
    cities = {}     # (省名, 市名) -> code
    rows = []
    seen = set()

    def add(code, name, level, parent_code):
        if code in seen:
            return
        seen.add(code)
        rows.append((code, name, level, parent_code))

    for item in raw:
        adm1, adm2 = item["adm1"], item["adm2"]

        # 省
        if adm1 not in provinces:
            p_code = f"P{len(provinces):02d}"
            provinces[adm1] = p_code
            add(p_code, adm1, LocationLevel.PROVINCE, None)
        p_code = provinces[adm1]

        # 市
        if (adm1, adm2) not in cities:
            c_code = f"{p_code}{len(cities):03d}"
            cities[(adm1, adm2)] = c_code
            add(c_code, adm2, LocationLevel.CITY, p_code)
        c_code = cities[(adm1, adm2)]

        # 区/县
        add(item["code"], item["name"], LocationLevel.DISTRICT, c_code)

    return rows


async def init_locations():
    print("开始拉取全国地区数据...")
    raw = await fetch_locations_from_qweather()
    print(f"总共拉取 {len(raw)} 条原始地区数据")

    if not raw:
        print("❌ 没有拉取到数据，中止")
        return

    rows = build_hierarchy(raw)
    print(f"整理为 {len(rows)} 条省/市/区层级数据")

    engine = create_async_engine(settings.mysql_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 清除旧数据
        await session.execute(delete(LocationDb))
        await session.commit()

        # 按 省→市→区 顺序插入，保证自引用外键 parent_code 有效
        for code, name, level, parent_code in rows:
            session.add(
                LocationDb(
                    code=code, name=name, level=level, parent_code=parent_code
                )
            )

        await session.commit()
        print(f"✅ 数据库初始化完成，共插入 {len(rows)} 条数据")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_locations())
