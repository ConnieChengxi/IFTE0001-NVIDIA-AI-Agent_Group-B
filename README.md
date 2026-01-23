# IFTE0001-NVIDIA-AI-Agent_Group-B
# NVIDIA Fundamental Valuation Project
Qiyun Sheng

This project contains a Python-based fundamental valuation analysis of NVIDIA Corporation (NVDA). The project is designed to be fully reproducible and automatically executable using GitHub Actions.


# Project Overview
The analysis uses Financial data collection from Yahoo Finance. Fundamental analysis are based on historical financial statements and the estimation of intrinsic firm value used cash flow–based valuation methods.  
The entire workflow is automated to ensure transparency and reproducibility. Project uses GitHub Actions to automatically run the analysis script. The script outputs key valuation metrics of NVIDIA， data analysis, and investment recommendation.  

# Environment and dependencies
python version 3.10  
key libraries: pandas, numpy, and yfinance  
All dependencies are automatically installed during workflow execution. No local setup is required to reproduce the results.

# How to run it manually:
1. Go to the **Actions** tab of this repository
2. Select **Run NVIDIA Analysis Script**
3. Click **Run workflow**
4. View the execution logs and results directly in the browser



Repository Structure
```text
.
├── analyse_nvidia.py        # Main valuation analysis script
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
└── .github/
    └── workflows/
        └── run-python.yml   # GitHub Actions workflow
