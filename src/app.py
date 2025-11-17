import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from pathlib import Path

# Set up Streamlit layout
st.set_page_config(layout="wide")

# Constants
DATA_PATH = Path.cwd() / "data" / "ads.parquet"


# Load data
@st.cache_data
def load_data(path):
    return pd.read_parquet(path)


def _min_max(series, fallback_min: int, fallback_max: int) -> tuple[int, int]:
    non_na = series.dropna()
    if non_na.empty:
        return fallback_min, fallback_max
    return int(non_na.min()), int(non_na.max())


df = load_data(DATA_PATH)

st.title("Interactive Data Explorer")


# Sidebar filters
def sidebar_filters(data):
    st.sidebar.header("Filters")

    year_min, year_max = _min_max(data["model_year"], 2015, 2025)
    model_year_range = st.sidebar.slider(
        "Model Year",
        year_min,
        year_max,
        (year_min, year_max),
    )

    km_min, km_max = _min_max(data["model_km"], 0, 300_000)
    model_km_range = st.sidebar.slider(
        "Model KM",
        km_min,
        km_max,
        (km_min, km_max),
    )

    price_min, price_max = _min_max(data["price"], 0, 1_000_000)
    price_range = st.sidebar.slider(
        "Price",
        price_min,
        price_max,
        (price_min, price_max),
    )

    brand_options = list(data["brand"].unique())
    selected_brands = st.sidebar.multiselect(
        "Brand", options=brand_options, default=brand_options
    )

    models = data[data["brand"].isin(selected_brands)]["model"].unique()
    selected_models = st.sidebar.multiselect("Model", options=models, default=models)

    safety_elements = [
        "Service",
        "Medlem",
        "Bruktbilgaranti",
        "Bytterett",
        "Programbil",
        "Garanti",
        "Tilstand",
    ]
    selected_safety_elements = [
        element for element in safety_elements if st.sidebar.checkbox(element)
    ]

    return (
        model_year_range,
        model_km_range,
        price_range,
        selected_brands,
        selected_models,
        selected_safety_elements,
    )


def filter_data(data, filters):
    (
        model_year_range,
        model_km_range,
        price_range,
        selected_brands,
        selected_models,
        selected_safety_elements,
    ) = filters

    filtered_df = data[
        (data["model_year"] >= model_year_range[0])
        & (data["model_year"] <= model_year_range[1])
        & (data["model_km"] >= model_km_range[0])
        & (data["model_km"] <= model_km_range[1])
        & (data["price"] >= price_range[0])
        & (data["price"] <= price_range[1])
    ]

    if selected_brands:
        filtered_df = filtered_df[filtered_df["brand"].isin(selected_brands)]

    if selected_models:
        filtered_df = filtered_df[filtered_df["model"].isin(selected_models)]

    if selected_safety_elements:
        selected_set = set(selected_safety_elements)
        filtered_df = filtered_df.dropna(subset=["safety_elements"]).loc[
            filtered_df["safety_elements"]
            .dropna()
            .apply(lambda x: selected_set.issubset(set(x)))
        ]

    return filtered_df


def plot_settings():
    st.sidebar.header("Plot Settings")
    x_axis = st.sidebar.selectbox(
        "X-Axis",
        options=filtered_df.columns,
        index=list(filtered_df.columns).index("model_km"),
    )
    y_axis = st.sidebar.selectbox(
        "Y-Axis",
        options=filtered_df.columns,
        index=list(filtered_df.columns).index("price"),
    )
    color_axis = st.sidebar.selectbox(
        "Color By",
        options=[None] + list(filtered_df.columns),
        index=list(filtered_df.columns).index("model_year") + 1,
    )
    show_scatter = st.sidebar.checkbox("Show Scatter", value=True)
    show_regression = st.sidebar.checkbox("Show Regression Line", value=True)
    degree = st.sidebar.slider("Polynomial Degree for Regression", 1, 5, 1)

    return x_axis, y_axis, color_axis, show_scatter, show_regression, degree


def plot_regression_lines(fig, df, x_axis, y_axis, color_axis, degree, colors):
    if color_axis and df[color_axis].nunique() <= 12:
        for category in df[color_axis].cat.categories:
            category_df = df[df[color_axis] == category]
            if not category_df.empty:
                add_regression_line(
                    fig, category_df, x_axis, y_axis, degree, colors[category]
                )
    else:
        add_regression_line(
            fig, df, x_axis, y_axis, degree, "blue"
        )  # Default color if no color axis or too many categories


def add_regression_line(fig, df, x_axis, y_axis, degree, line_color):
    X = df[[x_axis]].values
    y = df[y_axis].values
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    y_poly_pred = model.predict(X_poly)
    df["Regression"] = y_poly_pred
    fig.add_traces(
        px.line(df, x=x_axis, y="Regression", line_shape="linear")
        .update_traces(line=dict(color=line_color))
        .data
    )


# Get filters and filter data
filters = sidebar_filters(df)
filtered_df = filter_data(df, filters)

# Get plot settings
x_axis, y_axis, color_axis, show_scatter, show_regression, degree = plot_settings()

# Convert color_axis to categorical if it has fewer than 12 unique values
if color_axis and filtered_df[color_axis].nunique() <= 12:
    filtered_df[color_axis] = filtered_df[color_axis].astype("category")

# Plotly chart
hover_data = {
    "model_year": True,
    "model_km": True,
    "price": True,
    "tldr": True,
    "brand": True,
    "model": True,
    "id": True,
    "safety_elements": True,
    "is_leasing": True,
}

if show_scatter:
    fig = px.scatter(
        filtered_df, x=x_axis, y=y_axis, color=color_axis, hover_data=hover_data
    )
else:
    fig = px.scatter(filtered_df, x=x_axis, y=y_axis, hover_data=hover_data)
    fig.data = []

# Add regression lines if selected
if show_regression:
    color_discrete_map = None
    if color_axis and filtered_df[color_axis].nunique() <= 12:
        color_discrete_map = px.colors.qualitative.Plotly
        colors = {
            category: color_discrete_map[i % len(color_discrete_map)]
            for i, category in enumerate(filtered_df[color_axis].cat.categories)
        }
    else:
        colors = {
            "blue": "blue"
        }  # Default color if no color axis or too many categories

    plot_regression_lines(fig, filtered_df, x_axis, y_axis, color_axis, degree, colors)

# Ensure no negative values on the plot and set the limits based on actual data
fig.update_layout(
    xaxis_range=[0, None]
    if filtered_df[x_axis].min() < 0
    else [filtered_df[x_axis].min(), None],
    yaxis_range=[0, None]
    if filtered_df[y_axis].min() < 0
    else [filtered_df[y_axis].min(), None],
    autosize=True,
)

# Reset the x-axis and y-axis limits to be based on the actual data only
fig.update_xaxes(range=[filtered_df[x_axis].min(), filtered_df[x_axis].max()])
fig.update_yaxes(range=[filtered_df[y_axis].min(), filtered_df[y_axis].max()])

# Render the plot with full container width
st.plotly_chart(fig, use_container_width=True)

# Add paginated and sortable table
st.write("Filtered Data")

st.data_editor(
    filtered_df[
        [
            "brand",
            "model",
            "model_year",
            "model_km",
            "price",
            "tldr",
            "safety_elements",
            "link",
        ]
    ],
    column_config={
        "link": st.column_config.LinkColumn("link", display_text="Link to Ad"),
    },
    hide_index=True,
)
