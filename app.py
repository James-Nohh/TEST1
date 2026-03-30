import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="색소 베이스 사용량 대시보드", layout="wide")
st.title("색소 베이스 4자코드 사용량 분석 대시보드")

# --- 파일 업로드 ---
uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is None:
    st.info("CSV 파일을 업로드하면 대시보드가 표시됩니다.")
    st.stop()

# --- 데이터 로드 (인코딩 자동 시도) ---
for enc in ["utf-8", "euc-kr", "cp949"]:
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding=enc)
        break
    except (UnicodeDecodeError, Exception):
        continue
else:
    st.error("CSV 파일 인코딩을 인식할 수 없습니다.")
    st.stop()

# 빈 끝 컬럼 제거
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
df.columns = df.columns.str.strip()

# 컬럼명 표준화
col0, col1 = df.columns[0], df.columns[1]

# --- 분기별 데이터 정리 (long format) ---
quarters = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
metrics = ["count", "average_content", "max_content", "min_content"]
metric_labels = {
    "count": "사용 횟수",
    "average_content": "평균 함량",
    "max_content": "최대 함량",
    "min_content": "최소 함량",
}

rows = []
for _, row in df.iterrows():
    for q in quarters:
        entry = {
            "코드": str(row[col0]),
            "베이스명": row[col1],
            "분기": q.replace("2025-", ""),
        }
        for m in metrics:
            col_name = f"{q}_{m}"
            if col_name in df.columns:
                entry[metric_labels[m]] = pd.to_numeric(row[col_name], errors="coerce")
        rows.append(entry)

long_df = pd.DataFrame(rows)

# --- 연간 합계 / 평균 계산 ---
annual = (
    long_df.groupby(["코드", "베이스명"])
    .agg({"사용 횟수": "sum", "평균 함량": "mean"})
    .reset_index()
    .sort_values("사용 횟수", ascending=False)
)

# ===== 사이드바 필터 =====
st.sidebar.header("필터")
selected_bases = st.sidebar.multiselect(
    "베이스 선택 (미선택 시 전체)",
    options=df[col1].tolist(),
)

if selected_bases:
    long_df = long_df[long_df["베이스명"].isin(selected_bases)]
    annual = annual[annual["베이스명"].isin(selected_bases)]

# ===== KPI 카드 =====
st.markdown("---")
k1, k2, k3, k4 = st.columns(4)
total_count = long_df["사용 횟수"].sum()
avg_content = long_df["평균 함량"].mean()
num_bases = long_df["베이스명"].nunique()
max_single = long_df["최대 함량"].max()

k1.metric("총 사용 횟수", f"{total_count:,.0f}")
k2.metric("전체 평균 함량", f"{avg_content:.3f}")
k3.metric("베이스 종류 수", f"{num_bases}")
k4.metric("단일 최대 함량", f"{max_single:.2f}")

# ===== 차트 영역 =====
st.markdown("---")

# --- 1행: 연간 사용횟수 TOP 10 + 분기별 총 사용횟수 ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("연간 사용 횟수 TOP 10")
    top10 = annual.head(10)
    fig = px.bar(
        top10,
        x="사용 횟수",
        y="베이스명",
        orientation="h",
        color="사용 횟수",
        color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("분기별 총 사용 횟수 추이")
    q_total = long_df.groupby("분기", sort=False)["사용 횟수"].sum().reset_index()
    fig2 = px.bar(q_total, x="분기", y="사용 횟수", text="사용 횟수", color="분기")
    fig2.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig2.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# --- 2행: 분기별 평균 함량 히트맵 + 분기별 사용횟수 라인차트 ---
c3, c4 = st.columns(2)

with c3:
    st.subheader("베이스별 분기 평균 함량 히트맵")
    pivot = long_df.pivot_table(
        index="베이스명", columns="분기", values="평균 함량", aggfunc="mean"
    )
    # 연간 평균 기준 상위 15개만
    top_bases = pivot.mean(axis=1).sort_values(ascending=False).head(15).index
    pivot_top = pivot.loc[pivot.index.isin(top_bases)]
    fig3 = px.imshow(
        pivot_top,
        color_continuous_scale="YlOrRd",
        aspect="auto",
        labels=dict(color="평균 함량"),
    )
    fig3.update_layout(height=500)
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("베이스별 분기 사용 횟수 추이")
    top5_names = annual.head(5)["베이스명"].tolist()
    line_df = long_df[long_df["베이스명"].isin(top5_names)]
    fig4 = px.line(
        line_df,
        x="분기",
        y="사용 횟수",
        color="베이스명",
        markers=True,
    )
    fig4.update_layout(height=500)
    st.plotly_chart(fig4, use_container_width=True)

# --- 3행: 평균 함량 분포 + 원본 데이터 ---
c5, c6 = st.columns(2)

with c5:
    st.subheader("평균 함량 분포 (Box Plot)")
    fig5 = px.box(
        long_df,
        x="분기",
        y="평균 함량",
        color="분기",
        points="all",
    )
    fig5.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)

with c6:
    st.subheader("사용 횟수 vs 평균 함량 (Scatter)")
    fig6 = px.scatter(
        long_df,
        x="사용 횟수",
        y="평균 함량",
        color="베이스명",
        hover_name="베이스명",
        size="사용 횟수",
        size_max=20,
    )
    fig6.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig6, use_container_width=True)

# --- 원본 데이터 테이블 ---
st.markdown("---")
st.subheader("원본 데이터")
st.dataframe(df, use_container_width=True, height=400)
