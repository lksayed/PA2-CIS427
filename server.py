#importing libraries
import socket
import threading
import sys
import os
import sqlite3

SERVER_HOST = 'localhost'
SERVER_PORT = 9037
DB_FILE = 'pokemon_trading.db'
MAX_CLIENTS = 5

active_users = {}
db_lock = threading.Lock()

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
    
    # user table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            firstName TEXT,
            lastName TEXT,
            userName TEXT NOT NULL,
            password TEXT,
            USDBalance REAL NOT NULL,
            isRoot INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # pokemon cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PokemonCards (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            cardName TEXT NOT NULL,
            cardType TEXT NOT NULL,
            rarity TEXT NOT NULL,
            price REAL NOT NULL,
            count INTEGER NOT NULL,
            ownerID INTEGER,
            FOREIGN KEY (ownerID) REFERENCES Users(ID)
        )
    ''')       
    
    # new table for active user tracking
    cursor.execute('''
        SELECT COUNT(*) FROM Users
    ''')
    
    if cursor.fetchone()[0] == 0:
        users = [
            ('emailroot@ex.com', 'root', 'Root', 'User', 'Root01', 100.00, 1),
            ('emailmary@ex.com', 'mary', 'Mary', 'Smith', 'mary01', 100.00, 0),
            ('emailjohn@ex.com', 'john', 'John', 'Doe', 'john01', 100.00, 0),
            ('emailmoe@ex.com', 'moe', 'Moe', 'Howard', 'moe', 100.00, 0),
        ]
        
        cursor.executemany('''
                           INSERT INTO Users (email, userName, firstName, lastName, password, USDBalance, isRoot)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', users)
    
    conn.commit()
    
# client command    
def handle_client_command(command, conn, addr):
    tokens = command.split()
    
    if not tokens:
        return "400 Invalid command\n", False

    if tokens[0] == "LOGIN":
        return handle_login(tokens, conn, addr)
    
    elif tokens[0] == "LOGOUT":
        return handle_logout(conn)
    
    elif tokens[0] == "WHO":
        return handle_who(conn)
    
    elif tokens[0] == "LOOKUP":
        return handle_lookup(tokens, conn)
    
    elif tokens[0] == "DEPOSIT":
        return handle_deposit(tokens, conn)
    
    elif tokens[0] == "LIST":
        return handle_list(conn)
    
    elif tokens[0] == "SHUTDOWN":
        return handle_shutdown(conn)
    
    elif tokens[0] == "BUY":
        return handle_buy(tokens, conn)
    
    elif tokens[0] == "SELL":
        return handle_sell(tokens, conn)
    
    elif tokens[0] == "BALANCE":
        return handle_balance(tokens, conn)
    
    elif tokens[0] == "QUIT":
        return "200 OK\n", True
    
    else:
        return "400 Invalid command\n", False

# buy
def handle_buy(tokens, conn):
    if conn not in active_users:
        return "401 Unauthorized, please log in\n", False

    if len(tokens) != 7:
        return "403 Incorrect message format\n", False

    _, card_name, card_type, rarity, price, count, owner_id = tokens

    try:
        price = float(price)
        count = int(count)
        owner_id = int(owner_id)
    except ValueError:
        return "403 Invalid format\n", False

    username = active_users[conn][0]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT ID, USDBalance FROM Users WHERE userName = ?", (username,))
        user = cursor.fetchone()

        if not user:
            return "404 User does not exist\n", False

        balance = user[1]
        total_price = price * count

        if balance < total_price:
            return "402 Insufficient Funds\n", False

        # Deduct balance, add card to inventory
        new_balance = balance - total_price
        cursor.execute("UPDATE Users SET USDBalance = ? WHERE userName = ?", (new_balance, username))
        cursor.execute('''
            INSERT INTO PokemonCards (cardName, cardType, rarity, price, count, ownerID)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (card_name, card_type, rarity, price, count, user[0]))

        connection.commit()

    return f"200 OK\nBOUGHT: {count} {card_name}. New balance: ${new_balance:.2f}\n", False

# sell
def handle_sell(tokens, conn):
    if conn not in active_users:
        return "401 Unauthorized, please log in\n", False

    if len(tokens) != 5:
        return "403 Invalid format\n", False

    _, card_name, count, price, owner_id = tokens

    try:
        count = int(count)
        price = float(price)
    except ValueError:
        return "403 Invalid format\n", False

    username = active_users[conn][0]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT ID, count FROM PokemonCards WHERE cardName = ? AND ownerID = (SELECT ID FROM Users WHERE userName = ?)", 
                       (card_name, username))
        card = cursor.fetchone()

        if not card or card[1] < count:
            return "404 Not enough card balance\n", False

        card_id, current_count = card
        new_card_count = current_count - count

        cursor.execute("UPDATE PokemonCards SET count = ? WHERE ID = ?", (new_card_count, card_id))
        cursor.execute("SELECT USDBalance FROM Users WHERE userName = ?", (username,))
        user_balance = cursor.fetchone()[0]
        new_balance = user_balance + price * count
        cursor.execute("UPDATE Users SET USDBalance = ? WHERE userName = ?", (new_balance, username))

        connection.commit()

    return f"200 OK\nSOLD: {count} {card_name}. New balance: ${new_balance:.2f}\n", False

# balance
def handle_balance(tokens, conn):
    if conn not in active_users:
        return "401 Unauthorized, please log in\n", False

    if len(tokens) != 1:
        return "403 Invalid format\n", False

    username = active_users[conn][0]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT USDBalance FROM Users WHERE userName = ?", (username,))
        balance = cursor.fetchone()

    if not balance:
        return "404 User not found\n", False

    return f"200 OK\nCurrent balance: ${balance[0]:.2f}\n", False

def handle_login(tokens, conn, addr):
    if len(tokens) != 3:
        return "403 Message format error\n", False

    _, username, password = tokens
    
    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT ID, isRoot FROM Users WHERE userName = ? AND password = ?",
            (username, password),
        )
        
        user = cursor.fetchone()

        if not user:
            return "403 Wrong UserID or Password\n", False

        active_users[conn] = (username, addr, user[1])
        
        return "200 OK\n", False

def handle_logout(conn):
    if conn in active_users:
        del active_users[conn]
        
        return "200 OK\n", False
    
    return "401 Not logged in\n", False

def handle_who(conn):
    if conn not in active_users or not active_users[conn][2]:
        return "401 Unauthorized\n", False

    users_list = "\n".join(
        f"{info[0]} {info[1][0]}" for _, info in active_users.items()
    )
    
    return f"200 OK\nThe list of active users:\n{users_list}\n", False

def handle_lookup(tokens, conn):
    if conn not in active_users:
        return "401 Not logged in\n", False

    if len(tokens) != 2:
        return "403 Message format error\n", False

    card_name = tokens[1]
    username = active_users[conn][0]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute(
            '''
            SELECT ID, cardName, cardType, rarity, count
            FROM PokemonCards
            WHERE ownerID = (SELECT ID FROM Users WHERE userName = ?)
              AND cardName LIKE ?
            ''',
            (username, f"%{card_name}%")
        )
        
        matches = cursor.fetchall()

    if not matches:
        return "404 Your search did not match any records\n", False

    records = "\n".join(
        f"{record[0]} {record[1]} {record[2]} {record[3]} {record[4]}" for record in matches
    )
    
    return f"200 OK\nFound {len(matches)} match(es):\n{records}\n", False

def handle_deposit(tokens, conn):
    if conn not in active_users:
        return "401 Not logged in\n", False

    if len(tokens) != 2:
        return "403 Message format error\n", False

    try:
        amount = float(tokens[1])
        
        if amount <= 0:
            raise ValueError
    
    except ValueError:
        return "403 Invalid deposit amount\n", False

    username = active_users[conn][0]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE Users SET USDBalance = USDBalance + ? WHERE userName = ?",
            (amount, username)
        )
        connection.commit()
        
        cursor.execute("SELECT USDBalance FROM Users WHERE userName = ?", (username,))
        
        new_balance = cursor.fetchone()[0]

    return f"200 OK\nDeposit successful. New balance: ${new_balance:.2f}\n", False

def handle_list(conn):
    if conn not in active_users:
        return "401 Not logged in\n", False

    username, _, is_root = active_users[conn]

    with db_lock, sqlite3.connect(DB_FILE) as connection:
        cursor = connection.cursor()
        if is_root:
            cursor.execute(
                '''
                SELECT ID, cardName, cardType, rarity, count, ownerID
                FROM PokemonCards
                '''
            )
        else:
            cursor.execute(
                '''
                SELECT ID, cardName, cardType, rarity, count
                FROM PokemonCards
                WHERE ownerID = (SELECT ID FROM Users WHERE userName = ?)
                ''',
                (username,)
            )
        records = cursor.fetchall()

    if not records:
        return "404 No cards found\n", False

    card_list = "\n".join(
        " ".join(map(str, record)) for record in records
    )
    return f"200 OK\nThe list of records:\n{card_list}\n", False

def handle_shutdown(conn):
    if conn not in active_users or not active_users[conn][2]:
        return "401 Unauthorized\n", False

    return "200 OK\nShutting down server\n", True

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(10)

print(f"[*] Listening on {SERVER_HOST}:{SERVER_PORT}")

#server loop
def client_thread(client_socket, addr):
    print(f"Connection from {addr}")
    
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            print(f"Received from {addr}: {data}")
            response, shutdown = handle_client_command(data, client_socket, addr)

            client_socket.sendall(response.encode('utf-8'))
            if shutdown:
                break
        
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            break
    
    client_socket.close()
    
    if client_socket in active_users:
        del active_users[client_socket]
    
    print(f"Connection from {addr} closed")

def run_server():
    init_db()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(MAX_CLIENTS)
    
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    while True:
        try:
            client_socket, addr = server_socket.accept()
    
            thread = threading.Thread(target=client_thread, args=(client_socket, addr))
            thread.start()
    
        except KeyboardInterrupt:
            print("Server shutting down")
            server_socket.close()
    
            break

if __name__ == "__main__":
    run_server()