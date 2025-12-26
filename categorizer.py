"""
AI-powered transaction categorization

Copyright (c) 2025 Mattias Nyqvist
Licensed under the MIT License
"""

import anthropic
import os
import pandas as pd
from typing import List, Dict

# Default categories
DEFAULT_CATEGORIES = {
    'Food & Groceries': ['ICA', 'Coop', 'Hemköp', 'Willys', 'Supermarket', 'Groceries'],
    'Transportation': ['SL', 'Shell', 'Circle K', 'Gas', 'Fuel', 'Parking'],
    'Entertainment': ['Netflix', 'Spotify', 'HBO', 'Steam', 'Cinema'],
    'Shopping': ['H&M', 'Elgiganten', 'IKEA', 'Amazon', 'Clothing'],
    'Housing': ['Rent', 'Landlord', 'Electricity', 'Vattenfall', 'Water'],
    'Utilities': ['Telia', 'Telenor', 'Internet', 'Phone', 'Mobile'],
    'Dining Out': ['Restaurant', 'Max', 'McDonalds', 'Cafe', 'Bar'],
    'Healthcare': ['Apoteket', 'Pharmacy', 'Doctor', 'Hospital'],
    'Income': ['Salary', 'Deposit', 'Transfer In', 'Payment Received'],
    'Other': []
}


def categorize_transaction_simple(description: str) -> str:
    """
    Simple rule-based categorization using keywords.
    
    Args:
        description: Transaction description
        
    Returns:
        Category name
    """
    description_lower = description.lower()
    
    for category, keywords in DEFAULT_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in description_lower:
                return category
    
    return 'Other'


def categorize_transactions_bulk(df: pd.DataFrame, use_ai: bool = False, api_key: str = None) -> pd.DataFrame:
    """
    Categorize all transactions in DataFrame.
    
    Args:
        df: DataFrame with transactions
        use_ai: Whether to use AI categorization
        api_key: Anthropic API key (required if use_ai=True)
        
    Returns:
        DataFrame with 'category' column added
    """
    if use_ai and api_key:
        df['category'] = categorize_with_ai(df, api_key)
    else:
        df['category'] = df['description'].apply(categorize_transaction_simple)
    
    return df


def categorize_with_ai(df: pd.DataFrame, api_key: str) -> List[str]:
    """
    Use Claude AI to categorize transactions in bulk.
    
    Args:
        df: DataFrame with transactions
        api_key: Anthropic API key
        
    Returns:
        List of categories
    """
    client = anthropic.Anthropic(api_key=api_key)
    
    # Create prompt with transaction list
    transactions = df[['description', 'amount']].to_dict('records')
    
    prompt = f"""Categorize these financial transactions into appropriate categories.

Available categories:
- Food & Groceries
- Transportation
- Entertainment
- Shopping
- Housing
- Utilities
- Dining Out
- Healthcare
- Income
- Other

Transactions:
{format_transactions_for_prompt(transactions[:50])}  # Limit to 50 for prompt size

Return ONLY a comma-separated list of categories in the same order as transactions.
Example: Food & Groceries,Transportation,Entertainment,...

Categories:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        categories_text = response.content[0].text.strip()
        categories = [cat.strip() for cat in categories_text.split(',')]
        
        # If we got fewer categories than transactions, fill with rule-based
        if len(categories) < len(df):
            remaining = df.iloc[len(categories):]['description'].apply(categorize_transaction_simple).tolist()
            categories.extend(remaining)
        
        return categories[:len(df)]
        
    except Exception as e:
        print(f"AI categorization failed: {e}")
        # Fallback to rule-based
        return df['description'].apply(categorize_transaction_simple).tolist()


def format_transactions_for_prompt(transactions: List[Dict]) -> str:
    """Format transactions for AI prompt."""
    lines = []
    for i, t in enumerate(transactions, 1):
        lines.append(f"{i}. {t['description']} ({t['amount']} kr)")
    return "\n".join(lines)


def get_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get summary statistics by category.
    
    Returns:
        DataFrame with category summaries
    """
    summary = df.groupby('category').agg({
        'abs_amount': ['sum', 'mean', 'count']
    }).round(2)
    
    summary.columns = ['Total', 'Average', 'Count']
    summary = summary.sort_values('Total', ascending=False)
    
    return summary

def get_budget_status(df: pd.DataFrame, budgets: dict) -> pd.DataFrame:
    """
    Compare actual spending against budgets.
    
    Args:
        df: DataFrame with categorized transactions
        budgets: Dictionary of {category: budget_amount}
        
    Returns:
        DataFrame with budget comparison
    """
    # Get actual spending by category (expenses only)
    expense_df = df[df['type'] == 'Expense'].copy()
    actual = expense_df.groupby('category')['abs_amount'].sum()
    
    # Create comparison DataFrame
    budget_data = []
    for category, budget in budgets.items():
        spent = actual.get(category, 0)
        remaining = budget - spent
        percent_used = (spent / budget * 100) if budget > 0 else 0
        status = 'Over Budget' if spent > budget else 'Within Budget'
        
        budget_data.append({
            'Category': category,
            'Budget': budget,
            'Spent': spent,
            'Remaining': remaining,
            'Percent Used': percent_used,
            'Status': status
        })
    
    budget_df = pd.DataFrame(budget_data)
    budget_df = budget_df.sort_values('Percent Used', ascending=False)
    
    return budget_df


def suggest_budgets(df: pd.DataFrame, multiplier: float = 1.2) -> dict:
    """
    Suggest budgets based on historical spending.
    
    Args:
        df: DataFrame with categorized transactions
        multiplier: Budget multiplier (default 1.2 = 20% buffer)
        
    Returns:
        Dictionary of suggested budgets
    """
    expense_df = df[df['type'] == 'Expense'].copy()
    
    # Calculate number of months in data
    date_range_days = (expense_df['date'].max() - expense_df['date'].min()).days
    num_months = max(1, date_range_days / 30.44)
    
    # Calculate total spending per category
    total_spending = expense_df.groupby('category')['abs_amount'].sum()
    
    # Calculate monthly average
    monthly_avg = total_spending / num_months
    
    # Add buffer for unexpected expenses
    suggested = (monthly_avg * multiplier).round(-2)  # Round to nearest 100
    
    return suggested.to_dict()