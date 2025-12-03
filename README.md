# HCMUT MATHEMATICAL MODELING ASSIGNMENT
Our code is a Python-based tool designed to analyze **1-safe Petri Nets**. It implements various algorithms to handle state-space explosion and structural analysis, including explicit traversal, symbolic computation using Binary Decision Diagrams (BDD), and Integer Linear Programming (ILP).
## Features
This project implements the following tasks:

1.  **Parsing & Validation**: Reads `.pnml` files and validates the net structure (Task 1).
2.  **Explicit Reachability**: Computes reachable markings using **Bitmask BFS** for memory efficiency (Task 2).
3.  **Symbolic Reachability**: Uses **Binary Decision Diagrams (BDD)** to handle large state spaces efficiently (Task 3).
4.  **Deadlock Detection**: Combines **ILP (Integer Linear Programming)** with BDD checks to find deadlocks in the system (Task 4).
5.  **Optimization**: Finds a reachable marking that maximizes a weighted sum using ILP + BDD cut generation (Task 5).
## Setting up environment
### Requirements
- Python 3.8+
- `pip` (python package manager)

### Creating virtual environment
```sh
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```
### Installing dependencies
Ensure you have the `requirements.txt` in the code source.
```sh
pip install -r requirements.txt
```
*(Note: `dd` requires a C compiler. If installation fails, try `pip install dd --no-binary dd` or use a pre-compiled binary).*

## Execution
To run the program with the default sample file:
```sh
python main.py
```
To run with a specific `.pnml` file:
```
python main.py samples/your_file.pnml
```
## Example

## Further discussion

## Contribution
