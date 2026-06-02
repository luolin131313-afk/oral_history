import streamlit as st
import json
import os
import re
from zhipuai import ZhipuAI  # 接入智谱AI
from dotenv import load_dotenv  # 加载API密钥

# ===================== 1. 初始化智谱AI客户端（核心：接入API）=====================
try:
    # 云端部署：从Secrets拿密钥
    API_KEY = st.secrets["secrets"]["ZHIPU_API_KEY"]
    BASE_URL = st.secrets["secrets"]["ZHIPU_BASE_URL"]
except:
    # 本地电脑运行：读取.env文件
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv("ZHIPU_API_KEY")
    BASE_URL = os.getenv("ZHIPU_BASE_URL")

# 实例化客户端
client = ZhipuAI(api_key=API_KEY, base_url=BASE_URL)

# ===================== Web应用配置 =====================
st.set_page_config(
    page_title="扶贫纪实样本智能展示系统",
    page_icon="📚",
    layout="wide"
)
# ========== 新增：初始化会话状态，存储AI回答 ==========
if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = ""

# ===================== 加载结构化数据 =====================
@st.cache_data
def load_data():
    data_path = "web_data/archive_data.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


data = load_data()

# ===================== Web应用界面 =====================
st.title("📚 扶贫纪实样本智能展示系统")
st.markdown("---")

if data:
    # 侧边栏：样本导航 + 【红框位置：智能问答系统】
    st.sidebar.title("📋 样本导航")
    # st.sidebar.markdown(f"**样本名称：** {data['archive_name']}")
    st.sidebar.markdown(f"样本名称: 攻坚2020：一线扶贫干部亲历记")
    st.sidebar.markdown("---")

    # ========== 红框位置：智能问答系统核心代码 ==========
    st.sidebar.subheader("🤖 智能问答助手")
    st.sidebar.caption("基于扶贫纪实样本原文，智能回答你的问题")

    # 问题输入框（红框位置的核心交互区）
    user_question = st.sidebar.text_area(
        "请输入你的问题：",
        height=100,
        placeholder="例如：请介绍龙里三中的教育帮扶措施？"
    )

    # 提交按钮
    if st.sidebar.button("🚀 提交问题", use_container_width=True):
        if not user_question:
            st.sidebar.warning("⚠️ 请输入问题后再提交")
        else:
            # 加载状态提示
            with st.spinner("🧠 AI正在思考中..."):
                # 构建Prompt：严格限定AI只能基于样本原文回答
                prompt = f"""
                你是扶贫纪实样本的专属问答助手，**必须严格基于以下样本原文**回答问题，绝对不能编造内容。
                如果问题与样本无关，请直接说："抱歉，该问题与样本内容无关，无法回答"。

                样本原文：
                {data['raw_text']}

                用户问题：{user_question}

                请清晰、简洁、有条理地回答：
                """

                # 调用智谱AI API生成回答
                try:
                    response = client.chat.completions.create(
                        model="glm-4",  # 你之前测试通过的模型版本
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,  # 低温度保证回答严谨，符合样本属性
                        max_tokens=1000  # 控制回答长度
                    )
                    # 保存回答到会话状态，避免刷新丢失
                    st.session_state.ai_answer = response.choices[0].message.content
                except Exception as e:
                    st.session_state.ai_answer = f"❌ 回答失败：{str(e)}"

    # 显示AI回答（如果有）
    if "ai_answer" in st.session_state and st.session_state.ai_answer:
        st.sidebar.markdown("### 💡 AI回答：")
        st.sidebar.write(st.session_state.ai_answer)

    st.sidebar.markdown("---")
    # ========== 智能问答系统结束 ==========

    # 主界面：分栏展示（保持你原来的布局不变）
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 样本整体摘要")
        st.write(data["overall_summary"])

        st.subheader("🏷️ 核心关键词")
        # 适配深色主题的关键词样式
        keywords_html = " ".join([
                                     f"<span style='background-color:#2d3748; color:#f7fafc; padding:6px 12px; border-radius:6px; margin:3px; display:inline-block; border:1px solid #4a5568;'>{kw}</span>"
                                     for kw in data["keywords"]])
        st.markdown(keywords_html, unsafe_allow_html=True)

    with col2:
        st.subheader("📑 样本片段摘要")
        # 保留原有的搜索过滤功能（可选，你可以保留或删除）
        search_keyword = st.text_input("🔍 搜索片段摘要", placeholder="输入关键词过滤片段...")
        filtered_chunks = []
        for idx, summary in enumerate(data["chunk_summaries"]):
            if not search_keyword or search_keyword.lower() in summary.lower():
                filtered_chunks.append((idx + 1, summary))

        if search_keyword:
            st.caption(f"✅ 找到 {len(filtered_chunks)} 条匹配内容")

        for chunk_num, summary in filtered_chunks:
            if search_keyword:
                # 关键词高亮（适配深色主题）
                highlighted = re.sub(
                    re.escape(search_keyword),
                    lambda
                        m: f"<mark style='background-color:#3b82f6; color:white; padding:2px 4px; border-radius:3px;'>{m.group()}</mark>",
                    summary,
                    flags=re.IGNORECASE
                )
            else:
                highlighted = summary
            with st.expander(f"第{chunk_num}片段摘要"):
                st.markdown(highlighted, unsafe_allow_html=True)

else:
    st.error("❌ 未找到结构化数据，请先运行第四步准备数据！")