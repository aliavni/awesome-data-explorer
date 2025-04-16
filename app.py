"""
Awesome Data Explorer
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import altair as alt
import git
import pandas as pd
import requests
import streamlit as st
import yaml


@st.cache_resource
def get_awesome_data_repo() -> None:
    """Clone or update the awesome-data repository.

    This function clones the awesome-data repository if it doesn't exist locally,
    or pulls the latest changes if it already exists.
    """
    try:
        git.Git(".").clone("https://github.com/awesomedata/apd-core")
    except git.GitCommandError:
        repo = git.Repo("apd-core")
        repo.remotes.origin.pull()


@st.cache_data(show_spinner=False)
def get_categories_and_file_names() -> Tuple[Dict, List]:
    """
    Parses YAML files in the 'apd-core/core' directory to extract category and file information.

    This function scans the 'apd-core/core' directory recursively, identifies YAML files,
    and organizes them into categories based on their directory structure. It also handles
    YAML parsing errors and returns a list of files with syntax issues.

    Returns:
        Tuple[Dict, List]:
            - A dictionary where keys are category names and values are dictionaries
              mapping file names to their parsed YAML content.
            - A list of files that could not be parsed due to YAML syntax errors.
    """
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
                data_info = yaml.safe_load(f.read())
            except yaml.scanner.ScannerError:
                yml_errors.append(file)
                continue

        if category in category_files:
            category_files[category][file_name] = data_info
        else:
            category_files[category] = {file_name: data_info}

    return category_files, yml_errors


def get_data_info(category: str, file_name: str) -> Dict[str, Any]:
    """
    Retrieves and parses YAML data from a specified file within a given category.

    Args:
        category (str): The category folder name where the file is located.
        file_name (str): The name of the YAML file to be read.

    Returns:
        Dict[str, Any]: A dictionary containing the parsed data from the YAML file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        yaml.YAMLError: If there is an error parsing the YAML file.
    """
    p = Path("apd-core/core") / category / file_name

    with p.open() as f:
        data = yaml.safe_load(f.read())

    return data


def display_info_table(selected_data_info: Dict[str, Any]) -> None:
    """
    Displays a formatted table of selected data information using Streamlit.

    This function takes a dictionary containing metadata about selected data,
    converts it into a pandas DataFrame, and displays it in a Streamlit app
    with specific fields renamed and ordered for better readability.

    Args:
        selected_data_info (Dict[str, Any]): A dictionary containing metadata
            about the selected data. Expected keys include:
            - "title": The title of the data.
            - "description": A brief description of the data.
            - "keywords": Keywords associated with the data.

    Behavior:
        - Renames the keys "title", "description", and "keywords" to "Title",
          "Description", and "Keywords" respectively.
        - Displays only the fields that are available in the input dictionary.
        - Orders the displayed fields as "Title", "Description", and "Keywords".
        - Hides the index column in the displayed table.

    Returns:
        None
    """
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
def check_url(url: str) -> Tuple[bool, Any]:
    """
    Checks the validity of a given URL by sending a HEAD request.

    This function attempts to verify if the provided URL is accessible by making
    a HEAD request. It handles various exceptions related to SSL errors, connection
    issues, and schema problems. If the URL is missing a schema, it retries with
    an "https://" prefix.

    Args:
        url (str): The URL to check.

    Returns:
        Tuple[bool, Any]: A tuple where the first element is a boolean indicating
        whether the URL is valid, and the second element is either the response
        object (if valid) or an error message (if invalid).
    """
    try:
        response = requests.head(url, allow_redirects=False, timeout=5)
        return True, response
    except requests.exceptions.SSLError:
        return False, "SSL error"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.InvalidSchema:
        return False, "Invalid schema"
    except requests.exceptions.MissingSchema:
        return check_url("https://" + url)


def show_homepage(data_info: Dict[str, Any]) -> None:
    """
    Displays the homepage URL status and handles potential issues.

    This function takes a dictionary containing information about the homepage URL,
    checks its status, and displays appropriate messages based on the URL's state.
    It ensures that the URL uses HTTPS and handles various response scenarios such
    as redirects, connection issues, and SSL errors.

    Args:
        data_info (Dict[str, Any]): A dictionary containing the homepage URL under
                                    the key "homepage".

    Returns:
        None: This function does not return a value. It displays messages using
              the Streamlit library.
    """
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


def main() -> None:
    """
    The main function for the Awesome Data Explorer application.

    This function sets up the Streamlit page configuration, initializes the UI,
    and handles the logic for displaying data from the Awesome Public Datasets repository.
    It includes functionality for selecting topics and datasets, displaying dataset
    information, and visualizing data counts by topic.

    Features:
    - Sets the page title and layout.
    - Fetches the Awesome Public Datasets repository.
    - Retrieves categories and file names, handling YAML parsing errors.
    - Allows users to select a topic and dataset via the sidebar.
    - Displays dataset details, including title, image, and additional information.
    - Optionally shows a chart of data counts by topic.
    - Provides an "About" section with app and author information.
    - Displays warnings for YAML syntax issues in unprocessed files.

    Raises:
        None
    """
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

    selected_data_info = category_data[selected_data]

    title.title(selected_data_info["title"])
    data_image = selected_data_info.get("image")
    if data_image and data_image != "none":
        st.image(data_image, width=200)

    display_info_table(selected_data_info)
    show_homepage(selected_data_info)

    show_data_count_by_topic = st.sidebar.checkbox(
        "Show data count by topic", value=True
    )
    if show_data_count_by_topic:
        show_data_count_by_topic_chart(categories_and_files)

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


def show_data_count_by_topic_chart(categories_and_files: Dict[str, Dict]) -> None:
    """
    Displays a bar chart showing the count of data items by topic.

    This function takes a dictionary where the keys represent topics and the values
    are dictionaries containing data items. It calculates the number of data items
    for each topic and visualizes the counts using an Altair bar chart. The chart
    is displayed in a Streamlit application.

    Args:
        categories_and_files (Dict[str, Dict]): A dictionary where keys are topic names
            and values are dictionaries containing data items.

    Returns:
        None: This function does not return a value. It renders the chart directly
        in the Streamlit application.
    """
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


if __name__ == "__main__":
    main()
