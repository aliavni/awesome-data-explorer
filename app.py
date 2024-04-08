import altair as alt
import streamlit as st
import git
import pandas as pd
import requests
from pathlib import Path
import yaml


@st.cache_resource
def get_awesome_data_repo():
    try:
        git.Git(".").clone("https://github.com/awesomedata/apd-core")
    except git.GitCommandError:
        repo = git.Repo("apd-core")
        repo.remotes.origin.pull()


@st.cache_data(show_spinner=False)
def get_categories_and_file_names() -> dict:
    p = Path("apd-core/core")
    category_files = {}
    yml_errors = []
    for i in p.glob("**/*"):
        if i.is_dir():
            continue

        category, file_name = i.parts[-2:]

        file = Path("apd-core/core") / category / file_name

        with file.open() as f:
            try:
                data_info = yaml.load(f.read(), Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                yml_errors.append(file)
                continue

        if category in category_files:
            category_files[category][file_name] = data_info
        else:
            category_files[category] = {file_name: data_info}

    return category_files, yml_errors


def get_data_info(category: str, file_name: str) -> dict:
    p = Path("apd-core/core") / category / file_name

    with p.open() as f:
        data = yaml.load(f.read(), Loader=yaml.FullLoader)

    return data


def display_info_table(selected_data_info):
    selected_data_df = pd.DataFrame([selected_data_info])
    display_fields = {
        "title": "Title",
        "description": "Description",
        "keywords": "Keywords",
    }

    for key, display_title in display_fields.items():
        if key in selected_data_df.columns:
            selected_data_df.rename({key: display_title}, axis="columns", inplace=True)

    available_display_fields = list(
        set(selected_data_df.columns).intersection(set(display_fields.values()))
    )

    display_fields_order = {"Title": 0, "Description": 1, "Keywords": 2}
    available_display_fields.sort(key=lambda x: display_fields_order[x])

    display_df = selected_data_df[available_display_fields]
    st.markdown(display_df.style.hide(axis="index").to_html(), unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def check_url(url: str):
    try:
        response = requests.head(url, allow_redirects=False)
        return True, response
    except requests.exceptions.SSLError as e:
        return False, "SSL error"
    except requests.exceptions.ConnectionError as e:
        return False, "Connection error"
    except requests.exceptions.InvalidSchema as e:
        return False, "Invalid schema"
    except requests.exceptions.MissingSchema as e:
        return check_url("https://" + url)


def show_homepage(data_info):
    homepage = data_info["homepage"]

    if homepage.startswith("http:"):
        homepage = homepage.replace("http:", "https:")

    url_status, response = check_url(homepage)

    if url_status:
        if response.status_code in [301, 302]:
            st.info(f"{homepage}\n\nRedirects to {response.headers['Location']}")
        else:
            st.success(f"{homepage}")
    else:
        if response == "Connection error":
            st.error(f"{homepage}\n\nThere is a connection issue to this website.")
        elif response == "SSL error":
            st.warning(
                f"There might be an SSL issue with {homepage}\n\nProceed with caution!"
            )
        else:
            st.info(f"{homepage}")


def main():
    st.set_page_config(page_title="Awesome Data Explorer", layout="wide")

    title = st.empty()

    get_awesome_data_repo()

    categories_and_files, yml_errors = get_categories_and_file_names()

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

    show_data_count_by_topic = st.sidebar.checkbox(
        "Show data count by topic", value=True
    )

    selected_data_info = category_data[selected_data]

    title.title(selected_data_info["title"])
    data_image = selected_data_info.get("image")
    if data_image and data_image != "none":
        st.image(data_image, width=200)

    display_info_table(selected_data_info)

    show_homepage(selected_data_info)

    if show_data_count_by_topic:
        st.title("Data count by topic")
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

        text = chart.mark_text(
            align="left",
            baseline="middle",
            dx=3,
        ).encode(text="Number of data")

        st.altair_chart(chart + text, use_container_width=True)

    st.sidebar.title("About")
    st.sidebar.info(
        "This app shows available data in [Awesome Public Datasets]"
        "(https://github.com/awesomedata/awesome-public-datasets) repository.\n\n"
        "It is maintained by [Ali](https://www.linkedin.com/in/aliavnicirik/). "
        "Check the code at https://github.com/aliavni/awesome-data-explorer"
    )

    if yml_errors:
        st.warning(
            "Could not parse these files due to yml syntax issues: \n\n"
            + "\n\n".join([str(i) for i in yml_errors])
        )


if __name__ == "__main__":
    main()
