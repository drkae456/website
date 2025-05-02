"""
Examples of using rich, tabulate, and prettytable for better text formatting.
Run this script to see different formatting options in action.
"""
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from tabulate import tabulate
from prettytable import PrettyTable

# Sample data for our examples
data = [
    ["Python", "Advanced", 95],
    ["JavaScript", "Intermediate", 85],
    ["SQL", "Expert", 98],
    ["Ruby", "Beginner", 75]
]
headers = ["Language", "Level", "Score"]

def rich_examples():
    """Demonstrate rich formatting capabilities."""
    console = Console()
    
    # 1. Simple styled text
    console.print("\n[bold blue]Rich Formatting Examples[/bold blue]")
    console.print("[green]Success:[/green] Task completed!", style="bold")
    console.print("[red]Error:[/red] Something went wrong!", style="bold")
    
    # 2. Rich table
    table = RichTable(title="Skills Assessment")
    table.add_column("Language", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Score", justify="right", style="green")
    
    for row in data:
        table.add_row(*[str(x) for x in row])
    
    console.print(table)
    
    # 3. Panel with styled text
    text = Text.assemble(
        ("Important Notice\n", "bold red"),
        ("This is a highlighted message ", "yellow"),
        ("with multiple ", "green"),
        ("styles", "blue bold")
    )
    console.print(Panel(text))
    
    # 4. Markdown
    markdown = """
    # Markdown Support
    - **Bold text**
    - *Italic text*
    - `code blocks`
    - [links](https://example.com)
    """
    console.print(Markdown(markdown))

def tabulate_examples():
    """Demonstrate tabulate formatting capabilities."""
    print("\nTabulate Examples:")
    
    # Different table formats
    formats = ['grid', 'pipe', 'orgtbl', 'psql']
    
    for fmt in formats:
        print(f"\nFormat: {fmt}")
        print(tabulate(data, headers=headers, tablefmt=fmt))

def prettytable_examples():
    """Demonstrate PrettyTable formatting capabilities."""
    print("\nPrettyTable Examples:")
    
    # Basic table
    pt = PrettyTable()
    pt.field_names = headers
    for row in data:
        pt.add_row(row)
    
    # Customize the table
    pt.align["Language"] = "l"  # Left align language
    pt.align["Score"] = "r"     # Right align score
    pt.sortby = "Score"         # Sort by score
    pt.reversesort = True       # Sort in descending order
    
    print("\nCustomized Table (sorted by score):")
    print(pt)
    
    # HTML output
    print("\nHTML Output:")
    print(pt.get_html_string())

if __name__ == "__main__":
    print("Text Formatting Examples")
    print("=" * 50)
    
    rich_examples()
    tabulate_examples()
    prettytable_examples() 