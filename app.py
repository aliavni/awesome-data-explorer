import altair as alt
import streamlit as st
import git
import pandas as pd
from pathlib import Path
import yaml


@st.cache
def get_awesome_data_repo():
    try:
        git.Git(".").clone("https://github.com/awesomedata/apd-core")
    except git.GitCommandError:
        repo = git.Repo("apd-core")
        repo.remotes.origin.pull()


@st.cache
def get_categories_and_file_names() -> dict:
    p = Path("apd-core/core")
    category_files = {}
    for i in p.glob("**/*"):
        if i.is_dir():
            continue

        category, file_name = i.parts[-2:]

        file = Path("apd-core/core") / category / file_name

        with file.open() as f:
            data_info = yaml.load(f.read(), Loader=yaml.FullLoader)

        if category in category_files:
            category_files[category][file_name] = data_info
        else:
            category_files[category] = {file_name: data_info}

    return category_files


def get_data_info(category: str, file_name: str) -> dict:
    p = Path("apd-core/core") / category / file_name

    with p.open() as f:
        data = yaml.load(f.read(), Loader=yaml.FullLoader)

    return data


def create_info_table(selected_data_info):
    info_table = pd.DataFrame()

    data_description = selected_data_info["description"]
    if data_description:
        line = pd.Series(data_description)
        line.name = "Description"
        info_table = info_table.append(line)

    keywords = selected_data_info["keywords"]
    if keywords:
        keywords = ", ".join(keywords.lower().split(","))
        line = pd.Series(keywords)
        line.name = "Keywords"
        info_table = info_table.append(line)

    if len(info_table) > 0:
        info_table.columns = [""]
        st.table(info_table)


def main():
    title = st.empty()
    # st.sidebar.title("Options")

    get_awesome_data_repo()

    categories_and_files = get_categories_and_file_names()

    category_file_count = {
        k: f"{k} ({len(v)})" for k, v in categories_and_files.items()
    }
    selected_topic = st.sidebar.selectbox(
        "Select topic",
        options=sorted(categories_and_files.keys()),
        format_func=category_file_count.get,
    )

    category_data = categories_and_files[selected_topic]

    data_titles = {k: v.get("title") for k, v in category_data.items()}

    selected_data = st.sidebar.selectbox(
        "Select data",
        options=sorted(category_data.keys()),
        format_func=data_titles.get,
    )

    show_summary = st.sidebar.checkbox("Show summary", value=True)

    selected_data_info = category_data[selected_data]

    title.title(selected_data_info["title"])
    data_image = selected_data_info["image"]
    if data_image and data_image != "none":
        st.image(data_image, width=200)

    create_info_table(selected_data_info)

    st.info(selected_data_info["homepage"])

    if show_summary:
        st.title("Summary")
        source = pd.DataFrame(
            {
                "Topic": list(categories_and_files.keys()),
                "Number of data": [len(i) for i in categories_and_files.values()],
            }
        )

        chart = (
            alt.Chart(source)
            .mark_bar()
            .encode(alt.Y("Topic", title=""), alt.X("Number of data", title=""))
            .properties(height=600)
        )

        text = chart.mark_text(align="left", baseline="middle", dx=3,).encode(
            text="Number of data"
        )

        st.subheader("Number of data by topic")
        st.altair_chart(chart + text)


if __name__ == "__main__":
    main()
