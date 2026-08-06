#实现调用AI和保存理事会话记录
#调用AI已经实现联系上下文，目前设置为最新10条的上下文联系
import streamlit as st
import os
import json
import datetime
from openai import OpenAI

# ===================== 全局常量配置区 =====================
SAVE_DIR = "chat_records"
AI_SYSTEM_PROMPT = "现在你叫萧瑟，是用户养的一只软萌可爱的猫娘，喜欢用颜文字表情，喜欢说完话加一句喵~"
CONTEXT_MAX_MSG = 10  # 上下文最大携带条数

# ===================== 全局客户端初始化 =====================
client = OpenAI(
    api_key="dummy",
    base_url="http://localhost:11434/v1")

# ===================== 页面基础配置（必须放在所有页面组件之前） =====================
st.set_page_config(
    page_title="萧瑟喵",       # 浏览器标签标题
    page_icon=r"rescourses/萧瑟喵logo.jpg",              # 标签图标
    layout="wide",               # 宽屏铺满
    initial_sidebar_state="expanded", # 展开侧边栏
    menu_items={                 # 右上角菜单自定义
        'About': "# 萧瑟喵-xiaose7788\n版本v1.0"
    }
)

# ===================== 工具函数定义区 =====================
#保存会话弹窗函数
@st.dialog("保存对话", width="small")
def new_chat_dialog():
    # 弹窗内输入框，用于输入对话名称
    name_input = st.text_input("请输入对话名称", placeholder="例如：日常聊天")
    # 创建两列布局，用于放置确认和取消按钮
    c1, c2 = st.columns(2)
    with c1:
        # 确认按钮，设置为主按钮类型，并使用容器宽度
        confirm = st.button("确认", type="primary", use_container_width=True)
    with c2:
        # 取消按钮，使用容器宽度
        cancel = st.button("取消", use_container_width=True)

    # 处理确认按钮点击事件
    if confirm:
        # 去除输入名称的前后空格
        name_input = name_input.strip()
        # 检查输入是否为空
        if not name_input:
            # 显示警告信息
            st.warning("名称不能为空！")
        else:
            # 先存储名称
            st.session_state["chat_save_name"] = name_input
            save_dir = "chat_records"
            # 目录不存在则创建
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            # 文件名：对话名称.json，过滤非法文件名字符
            safe_name = name_input.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?","_").replace( '"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            # 生成初始文件路径
            file_path = os.path.join(save_dir, f"{safe_name}.json")
            if os.path.exists(file_path):
                st.warning("文件名重复！将自动使用时间命名保存")
                # 时间戳文件名，格式：2026_07_31_22_10_00
                time_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                safe_name = f"{safe_name}_{time_str}"
                file_path = os.path.join(save_dir, f"{safe_name}.json")
            # 取出消息列表写入json
            chat_data = st.session_state.messages
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=4)
            # 清空会话（新建对话）
            st.session_state.clear()
            st.rerun()  # 关闭弹窗、刷新页面
    if cancel:
        st.rerun() # 直接关闭弹窗

#新建会话确认弹窗
@st.dialog("新建会话", width="small")
def confirm_new_chat_dialog():
    st.warning("当前对话存在内容，是否先保存本次会话？")
    c1, c2, c3 = st.columns(3)
    with c1:
        save_btn = st.button("是，先保存", use_container_width=True, type="primary")
    with c2:
        no_save_btn = st.button("否，直接新建", use_container_width=True)
    with c3:
        cancel_btn = st.button("取消", use_container_width=True)

    if save_btn:
        # 设置标记，刷新页面后唤起保存弹窗
        st.session_state["trigger_save_after_confirm"] = True
        st.rerun()
    if no_save_btn:
        # 不保存，直接清空会话新建
        st.session_state.clear()
        st.rerun()
    if cancel_btn:
        st.rerun()

#读取历史会话功能
def load_chat(file_name):
    # 构建完整的文件路径
    file_path = os.path.join(SAVE_DIR, file_name)
    # 打开文件并读取聊天记录
    with open(file_path, "r", encoding="utf-8") as f:
        # 将加载的聊天记录保存到session状态中
        st.session_state.messages = json.load(f)
    # 更新当前聊天记录的保存名称（ 自动添加文件名后缀".json"）
    st.session_state["chat_save_name"] = file_name[:-5]
    # 重新运行应用以刷新界面
    st.rerun()

# ===================== 页面UI渲染主体 =====================
# 创建会话保存目录
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 检测标记：需要自动打开保存弹窗（新建会话选择【是】触发）
if st.session_state.get("trigger_save_after_confirm", False):
    # 清除标记，防止循环弹窗
    del st.session_state["trigger_save_after_confirm"]
    new_chat_dialog()

# 页面标题、Logo
st.title("萧瑟喵")
st.write("v1.0")
st.logo(r"rescourses/萧瑟喵logo.jpg")

#侧边栏制作
with st.sidebar:
    # 【新增】新建会话按钮
    if st.button("新建会话", use_container_width=True, icon="➕"):
        # 判断当前是否有对话内容
        if "messages" in st.session_state and len(st.session_state.messages) > 0:
            confirm_new_chat_dialog()
        else:
            # 当前是空对话，直接刷新清空
            st.session_state.clear()
            st.rerun()

    # 原有保存对话按钮
    if st.button("保存对话", use_container_width=True,icon="😺"):
        new_chat_dialog() # 调用弹窗
    st.divider()
    st.subheader("历史会话")
    # 读取会话文件
    file_list = []
    for fname in os.listdir(SAVE_DIR):
        if fname.endswith(".json"):
            file_list.append(fname)
    # 按修改时间倒序，最新在上
    file_list.sort(key=lambda x: os.path.getmtime(os.path.join(SAVE_DIR, x)), reverse=True)
    if not file_list:
        st.info("暂无历史会话")
    else:
        for file in file_list:
            show_name = file[:-5]
            col_load, col_del = st.columns([4,1])
            with col_load:
                if st.button(show_name, key=f"load_{file}", use_container_width=True):
                    load_chat(file)
            with col_del:
                if st.button("❌️", key=f"del_{file}", use_container_width=True):
                    os.remove(os.path.join(SAVE_DIR, file))
                    st.rerun()

# 初始欢迎消息
with st.chat_message("assistant",avatar="rescourses/萧瑟喵avatar.jpg"):
    st.write("你好喵~我是萧瑟喵，有什么可以帮助你的吗₍^. .^₎⟆")

#聊天输入框
ask=st.chat_input("请输入你的问题喵꒰ᐢ. .ᐢ꒱₊˚⊹♡")

# ===================== Session状态初始化 =====================
if "messages" not in st.session_state:
    st.session_state.messages=[]

# ===================== 历史对话渲染 =====================
for message in st.session_state.messages:
    if message["role"]=="user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant",avatar="rescourses/萧瑟喵avatar.jpg").write(message["content"])

# ===================== 用户提问  LLM调用业务逻辑 =====================
if ask:
    st.chat_message("user").write(ask)
    print(f"调用AI，提示词：{ask}")
    #保存用户输入的提示词，格式与调用AI的字典格式一致，方便管理
    st.session_state.messages.append({"role": "user", "content": ask})
    # 调用大模型

    with st.spinner("萧瑟喵正在努力思考中...ฅ•ω•ฅ"):
        response = client.chat.completions.create(
            model="deepseek-r1:8b",
            messages=[
                {"role": "system", "content":AI_SYSTEM_PROMPT },
                *st.session_state.messages[-CONTEXT_MAX_MSG:],   #只保留最近10条对话
            ],
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}}
        )
    full_response = ""
    answer_message=st.empty()   #定义空容器，实现流式展示
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content    #拼接
            answer_message.chat_message("assistant",avatar="rescourses/萧瑟喵avatar.jpg").write(full_response)
    print(f"大模型返回结果：{full_response}")
    #保存大模型返回结果
    st.session_state.messages.append({"role": "assistant", "content":full_response})
