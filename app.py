"""
Financial Dashboard - AI-powered transaction analysis and budget tracking

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from version import __version__, __author__, __license__
from data_processor import (
    load_transaction_file,
    calculate_summary_stats,
    filter_by_date_range,
    filter_by_type,
    get_date_range
)
from categorizer import (
    categorize_transactions_bulk,
    get_category_summary,
    DEFAULT_CATEGORIES,
    get_budget_status,
    suggest_budgets
)

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Financial Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None

if 'categorized' not in st.session_state:
    st.session_state.categorized = False

# Title and description
st.title("Financial Dashboard")
st.markdown("Upload your bank transactions and get instant AI-powered insights on your spending patterns.")

# Sidebar - File Upload
st.sidebar.header("Data Management")

uploaded_file = st.sidebar.file_uploader(
    "Upload Transaction Data",
    type=['csv', 'xlsx', 'xls'],
    help="Upload CSV or Excel file with columns: date, description, amount"
)

# Load sample data button
if st.sidebar.button("Load Sample Data"):
    try:
        sample_df = pd.read_csv('data/sample_transactions.csv')
        from data_processor import process_transactions
        st.session_state.df = process_transactions(sample_df)
        st.session_state.categorized = False
        st.sidebar.success("Sample data loaded successfully")
    except Exception as e:
        st.sidebar.error(f"Error loading sample data: {str(e)}")

# Process uploaded file
if uploaded_file is not None:
    df, error = load_transaction_file(uploaded_file)
    
    if error:
        st.sidebar.error(error)
    else:
        st.session_state.df = df
        st.session_state.categorized = False
        st.sidebar.success(f"Loaded {len(df)} transactions successfully")

# Main content
if st.session_state.df is None:
    # Welcome screen
    st.info("Upload your transaction data or load sample data to get started")
    
    st.markdown("### Expected File Format")
    st.markdown("""
    Your CSV or Excel file should contain these columns:
    - **date**: Transaction date (YYYY-MM-DD)
    - **description**: Transaction description
    - **amount**: Transaction amount (positive for income, negative for expenses)
    - **account** (optional): Account name
    
    Example:
    """)
    
    example_df = pd.DataFrame({
        'date': ['2024-12-01', '2024-12-02', '2024-12-03'],
        'description': ['Grocery Store', 'Salary Deposit', 'Restaurant'],
        'amount': [-450.50, 45000.00, -285.00],
        'account': ['Credit Card', 'Checking', 'Credit Card']
    })
    st.dataframe(example_df, use_container_width=True)
    
    # Footer in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Version:** {__version__}")
    st.sidebar.caption(f"© 2025 {__author__}")
    st.sidebar.caption("MIT License")
    
    st.stop()

# If we have data, show dashboard
df = st.session_state.df

# Sidebar - Categorization
st.sidebar.markdown("---")
st.sidebar.subheader("Categorization")

use_ai = st.sidebar.checkbox("Use AI Categorization", value=False, help="Use Claude AI for smarter categorization")

if st.sidebar.button("Categorize Transactions", type="primary"):
    with st.spinner("Categorizing transactions..."):
        api_key = os.environ.get("ANTHROPIC_API_KEY") if use_ai else None
        
        if use_ai and not api_key:
            st.sidebar.error("API key not configured. Using rule-based categorization.")
            use_ai = False
        
        st.session_state.df = categorize_transactions_bulk(df, use_ai=use_ai, api_key=api_key)
        st.session_state.categorized = True
        st.sidebar.success("Categorization complete")
        st.rerun()

# Check if categorized
if not st.session_state.categorized:
    st.warning("Click 'Categorize Transactions' in the sidebar to analyze your spending by category")

# Sidebar - Filters
st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

# Date range filter
min_date, max_date = get_date_range(df)
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    df = filter_by_date_range(df, pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))

# Transaction type filter
transaction_type = st.sidebar.radio(
    "Transaction Type",
    ["All", "Income", "Expense"],
    index=0
)

df = filter_by_type(df, transaction_type)

# Footer in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Version:** {__version__}")
st.sidebar.caption(f"© 2025 {__author__}")
st.sidebar.caption("MIT License")

# Main Dashboard
st.markdown("---")

# Summary metrics
stats = calculate_summary_stats(df)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Income",
        f"{stats['total_income']:,.0f} kr",
        help="Total income in selected period"
    )

with col2:
    st.metric(
        "Total Expenses",
        f"{stats['total_expenses']:,.0f} kr",
        help="Total expenses in selected period"
    )

with col3:
    st.metric(
        "Net Savings",
        f"{stats['net_savings']:,.0f} kr",
        delta=f"{stats['savings_rate']:.1f}%",
        help="Income minus expenses"
    )

with col4:
    st.metric(
        "Transactions",
        f"{stats['num_transactions']:,}",
        help="Number of transactions"
    )

st.markdown("---")

# Category analysis (if categorized)
if st.session_state.categorized and 'category' in df.columns:
    st.subheader("Spending by Category")
    
    # Filter out income for category analysis
    expense_df = df[df['type'] == 'Expense'].copy()
    
    if len(expense_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart
            category_totals = expense_df.groupby('category')['abs_amount'].sum().sort_values(ascending=False)
            
            fig_pie = px.pie(
                values=category_totals.values,
                names=category_totals.index,
                title="Expense Distribution by Category",
                hole=0.4
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart
            fig_bar = px.bar(
                x=category_totals.values,
                y=category_totals.index,
                orientation='h',
                title="Total Spending by Category",
                labels={'x': 'Amount (kr)', 'y': 'Category'}
            )
            fig_bar.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Category summary table
        st.markdown("### Category Summary")
        category_summary = get_category_summary(expense_df)
        st.dataframe(category_summary, use_container_width=True)
    else:
        st.info("No expenses to categorize in the selected date range")

st.markdown("---")

# Timeline visualization
st.subheader("Spending Over Time")

# Group by month
if 'month_name' in df.columns:
    monthly_data = df.groupby(['year', 'month', 'month_name', 'type'])['abs_amount'].sum().reset_index()
    monthly_data['period'] = monthly_data['year'].astype(str) + '-' + monthly_data['month'].astype(str).str.zfill(2)
    
    # Create line chart
    fig_timeline = px.line(
        monthly_data,
        x='period',
        y='abs_amount',
        color='type',
        title='Income vs Expenses Over Time',
        labels={'abs_amount': 'Amount (kr)', 'period': 'Month'},
        markers=True
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

# Recent transactions
st.subheader("Recent Transactions")

# Display options
num_to_show = st.selectbox("Number of transactions to display", [10, 25, 50, 100], index=0)

# Show transactions
display_df = df.head(num_to_show)[['date', 'description', 'amount', 'type']]
if 'category' in df.columns:
    display_df = df.head(num_to_show)[['date', 'description', 'amount', 'category', 'type']]

st.dataframe(display_df, use_container_width=True, hide_index=True)

# Budget Tracking Section
st.markdown("---")
st.subheader("Budget Tracking")

# Check if categorized
if not st.session_state.categorized:
    st.info("Categorize transactions first to use budget tracking")
else:
    # Import budget functions
    from budget_manager import render_budget_editor, render_budget_progress, create_budget_gauge_chart, DEFAULT_BUDGETS
    
    # Initialize budgets in session state
    if 'budgets' not in st.session_state:
        st.session_state.budgets = DEFAULT_BUDGETS.copy()
    
    # Tabs for budget management
    tab1, tab2 = st.tabs(["Budget Overview", "Set Budgets"])
    
    with tab1:
        # Calculate number of months in data
        date_range_days = (df['date'].max() - df['date'].min()).days
        date_range_months = max(1, round(date_range_days / 30.44))
        
        # Show period info
        st.info(f"Analyzing {date_range_months} months of data: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        
        # Get budget status
        budget_df = get_budget_status(df[df['type'] == 'Expense'], st.session_state.budgets)
        
        # Overall metrics
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Gauge chart with monthly average
            fig_gauge = create_budget_gauge_chart(budget_df, period_months=date_range_months)
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            # Period totals
            st.markdown("#### Period Totals")
            total_budget_period = budget_df['Budget'].sum() * date_range_months
            total_spent_period = budget_df['Spent'].sum()
            total_remaining = total_budget_period - total_spent_period
            
            col2a, col2b = st.columns(2)
            with col2a:
                st.metric("Budget (Period)", f"{total_budget_period:,.0f} kr")
                st.metric("Spent (Period)", f"{total_spent_period:,.0f} kr")
            with col2b:
                st.metric("Remaining", f"{total_remaining:,.0f} kr")
                if total_budget_period > 0:
                    st.metric("Usage", f"{(total_spent_period/total_budget_period*100):.1f}%")
            
            # Monthly averages
            st.markdown("---")
            st.markdown("#### Monthly Averages")
            monthly_budget = budget_df['Budget'].sum()
            monthly_spent = total_spent_period / date_range_months
            
            col2c, col2d = st.columns(2)
            with col2c:
                st.metric("Monthly Budget", f"{monthly_budget:,.0f} kr")
            with col2d:
                st.metric("Avg Monthly Spending", f"{monthly_spent:,.0f} kr")
        
        # Progress bars per category
        st.markdown("---")
        render_budget_progress(budget_df, period_months=date_range_months)
    
    with tab2:
        # Auto-suggest budgets
        if st.button("Suggest Budgets Based on Spending"):
            suggested = suggest_budgets(df)
            st.session_state.budgets = suggested
            st.success("Budgets updated based on your spending patterns")
            st.rerun()
        
        # Budget editor
        updated_budgets = render_budget_editor(st.session_state.budgets)
        
        if st.button("Save Budgets", type="primary"):
            st.session_state.budgets = updated_budgets
            st.success("Budgets saved successfully")
            st.rerun()

# AI Insights Section
st.markdown("---")
st.subheader("AI Insights & Recommendations")

# Check if categorized
if not st.session_state.categorized:
    st.info("Categorize transactions first to get AI-powered insights")
else:
    # Import AI insights functions
    from ai_insights import generate_spending_insights, render_insights_ui
    
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        st.warning("API key not configured. Set ANTHROPIC_API_KEY in .env file to use AI insights.")
    else:
        # Initialize insights in session state
        if 'ai_insights' not in st.session_state:
            st.session_state.ai_insights = None
        
        # Generate insights button
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("Generate AI Insights", type="primary", use_container_width=True):
                with st.spinner("Analyzing your spending patterns with AI..."):
                    # Calculate period
                    date_range_days = (df['date'].max() - df['date'].min()).days
                    date_range_months = max(1, round(date_range_days / 30.44))
                    
                    # Get budget data
                    if 'budgets' not in st.session_state:
                        from budget_manager import DEFAULT_BUDGETS
                        st.session_state.budgets = DEFAULT_BUDGETS.copy()
                    
                    budget_df = get_budget_status(df[df['type'] == 'Expense'], st.session_state.budgets)
                    
                    # Generate insights
                    insights = generate_spending_insights(
                        df=df,
                        budget_df=budget_df,
                        api_key=api_key,
                        period_months=date_range_months
                    )
                    
                    st.session_state.ai_insights = insights
                    st.success("AI insights generated successfully!")
        
        with col2:
            if st.session_state.ai_insights:
                st.caption("Last generated insights shown below. Click 'Generate AI Insights' to refresh.")
        
        # Display insights if available
        if st.session_state.ai_insights:
            st.markdown("---")
            render_insights_ui(st.session_state.ai_insights)
        else:
            st.info("Click 'Generate AI Insights' to get personalized recommendations based on your spending patterns.")

# Download data
st.markdown("---")
st.subheader("Export Data")

col1, col2 = st.columns(2)

with col1:
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    st.info("Excel export coming soon")