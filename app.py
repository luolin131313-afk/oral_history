import streamlit as st
import json
import os
import re
from zhipuai import ZhipuAI  # 接入智谱AI


# ===================== 新增：导入 Neo4j 和图谱可视化库 =====================
# ===================== 新增：导入 Neo4j 和图谱可视化库 =====================
from neo4j import GraphDatabase
from streamlit_agraph import agraph, Node, Edge, Config

# 安全修改：从 st.secrets 中读取连接配置，代码里不再出现明文密码
try:
    NEO4J_URI = st.secrets["secrets"]["NEO4J_URI"]
    NEO4J_USER = st.secrets["secrets"]["NEO4J_USER"]
    NEO4J_PASSWORD = st.secrets["secrets"]["NEO4J_PASSWORD"]
except Exception as e:
    # 如果本地没有配置 secrets，给出一个友好的提示
    st.error("❌ 未能在 st.secrets 中找到 Neo4j 配置，请检查 .streamlit/secrets.toml 文件")
    st.stop()

# ===================== 1. 初始化智谱AI客户端 =====================
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

# ===================== 优化版：从 Neo4j 查询图数据并美化视觉样式 =====================
# ===================== 终极修正版：从 Neo4j 查询图数据并转换为前端格式 =====================
@st.cache_data
def load_graph_from_neo4j():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    nodes = []
    edges = []
    seen_nodes = set()

    with driver.session() as session:
        # 查询所有的关键词节点以及它们之间的共现关系
        result = session.run("MATCH (n:Keyword)-[r:CO_OCCURS]->(m:Keyword) RETURN n, r, m")
        for record in result:
            n_node = record["n"]
            m_node = record["m"]

            # 🎨 节点颜色换成了你喜欢的紫色
            node_color = "#8b5cf6"

            # 建立源节点
            if n_node["name"] not in seen_nodes:
                nodes.append(Node(
                    id=n_node["name"], 
                    label=n_node["name"], 
                    size=22,              
                    color=node_color, 
                    font={'color': "#06b6d4"}  # ✨ 正确闭合的花括号和右括号
                ))
                seen_nodes.add(n_node["name"])

            # 建立目标节点
            if m_node["name"] not in seen_nodes:
                nodes.append(Node(
                    id=m_node["name"], 
                    label=m_node["name"], 
                    size=22, 
                    color=node_color, 
                    font={'color': '#ffc0cb'}  # ✨ 正确闭合的花括号和右括号
                ))
                seen_nodes.add(m_node["name"])

            # 建立边（连线）
            edges.append(Edge(
                source=n_node["name"], 
                target=m_node["name"], 
                label=""
            ))

    driver.close()
    return nodes, edges


# ===================== Web应用界面 =====================
st.title("📚 扶贫纪实样本智能展示系统")
st.markdown("---")

if data:
    # 侧边栏：样本导航
    st.sidebar.title("📋 样本导航")
    st.sidebar.markdown(f"样本名称: 攻坚2020：一线扶贫干部亲历记")
    st.sidebar.markdown("---")

    # 智能问答系统
    st.sidebar.subheader("🤖 智能问答助手")
    st.sidebar.caption("基于扶贫纪实样本原文，智能回答你的问题")

    user_question = st.sidebar.text_area(
        "请输入你的问题：",
        height=100,
        placeholder=""
    )

    if st.sidebar.button("🚀 提交问题", use_container_width=True):
        if not user_question:
            st.sidebar.warning("⚠️ 请输入问题后再提交")
        else:
            with st.spinner("🧠 AI正在思考中..."):
                prompt = f"""
                你是扶贫纪实样本的专属问答助手，**必须严格基于以下样本原文**回答问题，绝对不能编造内容。
                如果问题与样本无关，请直接说："抱歉，该问题与样本内容无关，无法回答"。

                样本原文：
                {data['raw_text']}

                用户问题：{user_question}

                请清晰、简洁、有条理地回答：
                """
                try:
                    response = client.chat.completions.create(
                        model="glm-4.7",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=1000
                    )
                    st.session_state.ai_answer = response.choices[0].message.content
                except Exception as e:
                    st.session_state.ai_answer = f"❌ 回答失败：{str(e)}"

    if "ai_answer" in st.session_state and st.session_state.ai_answer:
        st.sidebar.markdown("### 💡 AI回答：")
        st.sidebar.write(st.session_state.ai_answer)

    st.sidebar.markdown("---")

    # 主界面：分栏展示
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 样本整体摘要")
        st.write(data["overall_summary"])

        # ===================== 核心修改位置：用 Neo4j 图谱替换静态标签 =====================
        st.subheader("🕸️ 核心关键词知识图谱")
        st.caption("基于文本片段共现关系生成，支持鼠标滚轮缩放、拖拽节点探索")

        with st.spinner("正在从 Neo4j 渲染图谱网络..."):
            nodes_data, edges_data = load_graph_from_neo4j()

            # 配置图谱的外观和弹簧物理效果
            
            graph_config = Config(
                width=650,
                height=500,
                directed=False,   # 共现关系通常是无向的
                physics=True,     # 开启物理力导向布局
                hierarchical=False,
                
                # ✨ 终极杀招：在这里加入全局字体控制，彻底锁死亮白色
                # 这会强制覆盖掉框架底层所有的暗色、半透明滤镜
                font={
                    'color': '#ffffff',    # 强制全局文字为纯白色
                    'size': 14,            # 稍微加大字号，更清晰
                    'face': 'sans-serif'   # 使用标准无衬线字体
                }
            )

            # 渲染图谱到页面上
            if nodes_data and edges_data:
                agraph(nodes=nodes_data, edges=edges_data, config=graph_config)
            else:
                st.warning("⚠️ 未能加载到图谱数据")
        # ===================================================================================

    with col2:
        st.subheader("📑 样本片段摘要")
        search_keyword = st.text_input("🔍 搜索片段摘要", placeholder="输入关键词过滤片段...")
        filtered_chunks = []
        for idx, summary in enumerate(data["chunk_summaries"]):
            if not search_keyword or search_keyword.lower() in summary.lower():
                filtered_chunks.append((idx + 1, summary))

        if search_keyword:
            st.caption(f"✅ 找到 {len(filtered_chunks)} 条匹配内容")

        for chunk_num, summary in filtered_chunks:
            if search_keyword:
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
