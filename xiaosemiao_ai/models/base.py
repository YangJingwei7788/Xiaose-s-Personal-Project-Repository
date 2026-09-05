"""ORM 基类与通用类型"""
from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""


# 主键类型：MySQL 使用 BIGINT 自增；SQLite 测试环境退化为 INTEGER 以支持 rowid 自增
BigIntPK = BigInteger().with_variant(Integer, "sqlite")