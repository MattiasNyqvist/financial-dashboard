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