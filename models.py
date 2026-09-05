"""数据表结构与默认种子数据定义。"""
from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类，create_all 依据它建表。"""


class GoodsCategory(Base):
    """业务品类表：type 1=回收 2=售卖，status 1=显示 0=隐藏"""

    __tablename__ = "goods_category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    type = Column(Integer, nullable=False, default=1)
    sort = Column(Integer, nullable=False, default=0)
    status = Column(Integer, nullable=False, default=1)
    image = Column(Text, nullable=False, default="")
    create_time = Column(Text, nullable=False)

    def to_dict(self) -> dict:
        """转为接口返回所需的字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "sort": self.sort,
            "status": self.status,
            "image": self.image,
        }


class CustomerBook(Base):
    """客户预约表：book_type 1=回收 2=购买，status 0=未处理 1=已处理"""

    __tablename__ = "customer_book"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=False)
    book_type = Column(Integer, nullable=False, default=1)
    need_content = Column(Text, nullable=False, default="")
    create_time = Column(Text, nullable=False)
    status = Column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        """转为接口返回所需的字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "book_type": self.book_type,
            "need_content": self.need_content,
            "create_time": self.create_time,
            "status": self.status,
        }


class Setting(Base):
    """门店配置表：key-value 键值对存储"""

    __tablename__ = "settings"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False, default="")

RECYCLE_CATEGORIES = [
    "实木床", "床垫", "沙发", "衣柜", "桌椅",
    "茶几/电视柜", "书柜/书架", "家用小家电", "空调/冰箱/洗衣机", "厨卫用品",
    "收纳家居", "办公家具",
]

# 默认售卖品类（后台可增删改）
SELL_CATEGORIES = [
    "实木床", "床垫", "沙发", "衣柜", "桌椅",
    "茶几/电视柜", "书柜/书架", "家用小家电", "办公家具", "户外家具",
]

SEED_CATEGORIES = {"recycle": RECYCLE_CATEGORIES, "sell": SELL_CATEGORIES}

# 默认门店配置（后台可修改）
DEFAULT_SETTINGS = {
    "shop_name": "乐享二手家具回收·售卖",
    "slogan": "上门回收 · 实惠售卖 · 让旧家具焕发新生",
    "home_intro": "本店专业从事二手家具及家居用品的回收与售卖，品类齐全、价格实惠、上门服务，让闲置物品重新流转，让您买得放心、卖得省心。",
    "recycle_intro": "支持上门回收各类家具、家居用品及配套家电，数量不限、随叫随到，欢迎电话或在线预约。",
    "sell_intro": "在售二手家具均经清洁整理，品类丰富、性价比高，支持到店选购与预约看货。",
    "about_intro": "本店专注二手家具回收与售卖多年，坚持诚信经营、童叟无欺，为您提供便捷的上门回收与实惠的二手好物。",
    "service_advantages": "品类齐全\n上门回收\n价格公道\n诚信经营",
    "door_service": "市区范围内免费上门看货、上门回收，大件家具可协助搬运，回收结算快速透明。",
    "service_flow": "1. 电话/在线预约\n2. 上门看货估价\n3. 确认成交搬运\n4. 现场结算",
    "address": "幸福路 88 号（示例地址，可在后台修改）",
    "phone": "138-0000-0000",
    "work_time": "每天 09:00 - 21:00",
    "carousel_images": "[]",
    "carousel_captions": "[]",
    "admin_password": "admin123",
}

# 允许通过接口修改的公开配置键（后台密码除外）
PUBLIC_SETTING_KEYS = [
    "shop_name", "slogan", "home_intro", "recycle_intro", "sell_intro",
    "about_intro", "service_advantages", "door_service", "service_flow",
    "address", "phone", "work_time", "carousel_images", "carousel_captions",
]