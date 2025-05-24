# Day-Ahead Electricity Price Heatmap App

This Streamlit web application is designed to visualize Day-Ahead electricity prices across various European bidding zones. It utilizes the ENTSOE Transparency Platform API to fetch real-time and historical price data, presenting it in an interactive heatmap format.

## Features

*   **Single Day Selection:** Easily select a specific day to view prices.
*   **Multi-Country Selection:** Choose any number of European countries (bidding zones) for comparison.
*   **Interactive Heatmap:** Displays hourly electricity prices with a clear color scale (green for negative/low prices, red for high prices).
*   **Price Spread Display:** The daily price spread (difference between maximum and minimum price) for each zone is shown directly on the X-axis below the country name.
*   **Custom Theme:** The application is configured with a clean white background and black text for optimal readability.
*   **Custom Font & Size:** Global font family and size are easily customizable within the application code.

## Technologies Used

*   [Python 3.x](https://www.python.org/)
*   [Streamlit](https://streamlit.io/) - For rapidly building interactive web applications.
*   [Pandas](https://pandas.pydata.org/) - For data manipulation and analysis.
*   [Entsoe-PandasClient](https://pypi.org/project/entsoe-pandas/) - A Python client for the ENTSOE Transparency Platform API.
*   [Plotly](https://plotly.com/python/) - For creating interactive and visually appealing graphs.

## How to Run Locally

To run this application on your local machine, follow these steps:

1.  **Clone the repository:**
    Open your terminal (e.g., VS Code integrated terminal) and navigate to the directory where you want to store the project. Then run:
    ```bash
    git clone https://github.com/YOUR_GITHUB_USERNAME/entsoe_heatmap_app.git
    cd entsoe_heatmap_app
    ```
    *(Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.)*

2.  **Create and activate a virtual environment:**
    It is highly recommended to use a virtual environment to manage your project's dependencies.
    ```bash
    python -m venv venv
    # On Windows (PowerShell):
    .\venv\Scripts\activate
    # On macOS / Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    With your virtual environment activated, install all necessary libraries from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up ENTSOE API Token:**
    The application requires an ENTSOE API token to access data.
    *   Create a folder named `.streamlit` (note the leading dot!) in the project's root directory (where `app.py` is located).
    *   Inside the `.streamlit` folder, create a file named `secrets.toml`.
    *   Add your API token to `secrets.toml` in the following format (replace `YOUR_ENTSOE_TOKEN` with your actual token):
        ```toml
        # .streamlit/secrets.toml
        entsoe_token = "YOUR_ENTSOE_TOKEN"
        ```
    **Important:** The `secrets.toml` file contains sensitive information and is intentionally excluded from the Git repository via `.gitignore`. **Never commit your API token directly to GitHub!**

5.  **Run the application:**
    With your virtual environment activated, launch the Streamlit application:
    ```bash
    streamlit run app.py
    ```
    This will open the application in your default web browser (usually at `http://localhost:8501`).

## Deployment on Streamlit Community Cloud

This application can be easily deployed to the free [Streamlit Community Cloud](https://share.streamlit.io/) platform.

When deploying the app:
1.  Connect your GitHub repository.
2.  Select the `main` branch and `app.py` as the main file path.
3.  **Crucial Step: Add your ENTSOE API Token as a "secret".** In the "Advanced settings" or "Secrets" section of your app's settings on Streamlit Cloud, add a new secret with the exact key `entsoe_token` and its value (your actual token).
    ```
    entsoe_token = "YOUR_ENTSOE_TOKEN"
    ```
    (This secret replaces the local `secrets.toml` for cloud deployment.)

---

**Remember to:**
1.  Save this content as `README.md` in the root of your `entsoe_heatmap_app` project folder.
2.  Add and commit it to your Git repository:
    ```bash
    git add README.md
    git commit -m "Add English README.md"
    ```
3.  Push your changes to GitHub:
    ```bash
    git push
    ```