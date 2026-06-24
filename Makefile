# FastAPI 项目常用命令
# 用法：make <命令名>，例如 make dev、make migrate msg="create posts table"
#
# 说明：默认 ENV=dev，要操作生产库时前面加 ENV=prod，例如：
#   ENV=prod make upgrade

ENV ?= dev

.PHONY: help dev migrate upgrade downgrade current history showtable

help:  ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-12s %s\n", $$1, $$2}'

dev:  ## 启动开发服务器（热重载）
	ENV=$(ENV) uvicorn src.main:app --reload --host 0.0.0.0 --port 8106

migrate:  ## 生成迁移脚本：make migrate msg="create posts table"
	ENV=$(ENV) alembic revision --autogenerate -m "$(msg)"

upgrade:  ## 应用所有未执行的迁移到最新
	ENV=$(ENV) alembic upgrade head

downgrade:  ## 回退一个版本
	ENV=$(ENV) alembic downgrade -1

current:  ## 查看当前数据库的迁移版本
	ENV=$(ENV) alembic current

history:  ## 查看迁移历史
	ENV=$(ENV) alembic history

showtable:  ## 查看某张表结构：make showtable t=posts
	ENV=$(ENV) python scripts/show_table.py $(t)

install:  ## 装依赖并同步到 requirements: make install p=openpyxl
	pip install $(p) && pip freeze | grep -i $(p) >> requirements.txt

