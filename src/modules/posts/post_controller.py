from http import HTTPStatus
from fastapi import Depends, HTTPException, UploadFile

from src.common.dependencies import CurrentUser, DbDep
from src.common.pagination import PageQuery, PageResp
from src.common.route import create_router
from src.modules.posts.post_dto import PostBatchCreate, PostCreate, PostResp, PostUpdate
from src.modules.posts.post_model import PostDB
from src.modules.posts.post_service import PostService

router = create_router(prefix="/posts", tags=["文章模块"])

svc = PostService()

async def get_own_post(post_id: int, db: DbDep, current_user: CurrentUser):
    db_post = await svc.get_by_id(db, post_id)

    if not db_post:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")

    if db_post.author_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="该文章不属于您")
    
    return db_post

@router.post("", response_model=PostResp)
async def create_post(payload: PostCreate, current_user: CurrentUser, db: DbDep):
    return await svc.create(db, payload, author_id=current_user.id)

@router.get("/{post_id}", response_model=PostResp)
async def get_post(post_id: int, db: DbDep):
    post = await svc.get_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")
    return post

@router.get("", response_model=PageResp[PostResp])
async def get_all_posts(db: DbDep, params: PageQuery = Depends(), author_id: int | None = None):
    return await svc.get_all(db, params, author_id=author_id)

@router.put("/{post_id}", response_model=PostResp)
async def update_post(payload: PostUpdate, db: DbDep, db_post: PostDB = Depends(get_own_post)):
    return await svc.update_post(db, payload=payload, db_post=db_post)

@router.delete("/{post_id}")
async def delete_post(db: DbDep, db_post: PostDB = Depends(get_own_post)):    
    return await svc.delete_post(db, db_post=db_post)

@router.post("/batch", response_model=list[PostResp])
async def create_batch_posts(payloads: PostBatchCreate, current_user: CurrentUser, db: DbDep):
    if not payloads.posts:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不能为空")
    return await svc.create_batch(db, payloads=payloads, author_id=current_user.id)

@router.post("/import")
async def import_posts(file: UploadFile, db: DbDep):
   return svc.import_from_excel(db, file=file)

