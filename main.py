from fastmcp import FastMCP
import sqlite3
from datetime import datetime
from pathlib import Path

mcp = FastMCP(name="Expense Tracker")

# Database setup
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "expenses.db"


def init_db():
    """Initialize the database with a simple expenses table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


@mcp.tool()
def add_expense(amount: float, category: str, description: str = "", subcategory: str = "", date: str = None) -> str:
    """
    Add a new expense

    Args:
        amount: The expense amount in INR
        category: Category (e.g., "Food", "Transport", "Shopping")
        description: What you spent on
        subcategory: Optional subcategory (e.g., "Groceries", "Fuel")
        date: Date in YYYY-MM-DD format (defaults to today)
    """
    if amount <= 0:
        return "Error: Amount must be positive"

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO expenses (amount, category, subcategory, description, date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (amount, category, subcategory, description, date, now))

    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return f"✓ Expense added! ID: {expense_id}, ${amount:.2f} - {category}, Date: {date}"


@mcp.tool()
def get_expenses(start_date: str = None, end_date: str = None, category: str = None) -> str:
    """
    Get expenses with optional filters

    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        category: Filter by category (optional)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, id DESC"

    cursor.execute(query, params)
    expenses = cursor.fetchall()
    conn.close()

    if not expenses:
        return "No expenses found"

    result = f"Found {len(expenses)} expense(s):\n\n"
    total = 0

    for exp in expenses:
        total += exp['amount']
        result += f"ID: {exp['id']} | ${exp['amount']:.2f} | {exp['category']}"
        if exp['subcategory']:
            result += f" > {exp['subcategory']}"
        if exp['description']:
            result += f" | {exp['description']}"
        result += f" | {exp['date']}\n"

    result += f"\nTotal: ${total:.2f}"
    return result


@mcp.tool()
def edit_expense(expense_id: int, amount: float = None, category: str = None, subcategory: str = None, description: str = None, date: str = None) -> str:
    """
    Edit an existing expense

    Args:
        expense_id: The ID of the expense to edit
        amount: New amount (optional) in INR
        category: New category (optional)
        subcategory: New subcategory (optional)
        description: New description (optional)
        date: New date in YYYY-MM-DD format (optional)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if expense exists
    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    if not cursor.fetchone():
        conn.close()
        return f"Error: Expense with ID {expense_id} not found"

    updates = []
    params = []

    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)

    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if subcategory is not None:
        updates.append("subcategory = ?")
        params.append(subcategory)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if date is not None:
        updates.append("date = ?")
        params.append(date)

    if not updates:
        conn.close()
        return "Error: No fields to update"

    params.append(expense_id)
    query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()

    return f"✓ Expense ID {expense_id} updated!"


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """
    Delete an expense

    Args:
        expense_id: The ID of the expense to delete
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    if cursor.rowcount == 0:
        conn.close()
        return f"Error: Expense with ID {expense_id} not found"

    conn.commit()
    conn.close()
    return f"✓ Expense ID {expense_id} deleted!"


@mcp.tool()
def get_summary(start_date: str = None, end_date: str = None) -> str:
    """
    Get expense summary by category

    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT category, SUM(amount) as total, COUNT(*) as count FROM expenses WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " GROUP BY category ORDER BY total DESC"

    cursor.execute(query, params)
    summary = cursor.fetchall()
    conn.close()

    if not summary:
        return "No expenses found"

    result = "Expense Summary by Category:\n\n"
    grand_total = 0

    for row in summary:
        result += f"{row['category']}: ${row['total']:.2f} ({row['count']} expenses)\n"
        grand_total += row['total']

    result += f"\nGrand Total: ${grand_total:.2f}"
    return result


@mcp.resource("expense://categories")
def get_categories() -> str:
    """Common expense categories with examples"""
    categories = {
        "Food": ["Groceries", "Restaurants", "Coffee"],
        "Transport": ["Fuel", "Public Transit", "Uber/Taxi"],
        "Shopping": ["Clothing", "Electronics", "General"],
        "Bills": ["Rent", "Electricity", "Internet", "Phone"],
        "Entertainment": ["Movies", "Games", "Hobbies"],
        "Healthcare": ["Medicine", "Doctor", "Gym"],
        "Education": ["Books", "Courses", "Supplies"],
        "Other": ["Miscellaneous"]
    }

    result = "Common Expense Categories:\n\n"
    for category, subcats in categories.items():
        result += f"• {category}\n"
        result += f"  Subcategories: {', '.join(subcats)}\n\n"

    return result


if __name__ == "__main__":
    mcp.run()
