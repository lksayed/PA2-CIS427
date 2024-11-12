import socket
import sqlite3
import os

#server config
SERVER_HOST = 'localhost'
SERVER_PORT = 9037
DB_FILE = 'pokemon_trading.db'

#database init
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    #user table
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

    #pokemon cards table
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

    #check for users, if none: create first user
    cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = cursor.fetchone()[0]
    if user_count == 0:
        cursor.execute('''
            INSERT INTO Users (email, firstName, lastName, userName, password, USDBalance, isRoot)
            VALUES ('admin@example.com', 'Admin', 'User', 'admin', 'password', 100.0, 1)
        ''')

    conn.commit()
    conn.close()


#handling user commands
def handle_client_command(command, conn, addr):
    tokens = command.split()
    if tokens[0] == 'BUY':
        return handle_buy(tokens, conn)
    elif tokens[0] == 'SELL':
        return handle_sell(tokens, conn)
    elif tokens[0] == 'BALANCE':
        return handle_balance(tokens, conn)
    elif tokens[0] == 'LIST':
        return handle_list(tokens, conn)
    elif tokens[0] == 'SHUTDOWN':
        return "200 OK\n", True
    elif tokens[0] == 'QUIT':
        return "200 OK\n", False
    else:
        return "400 Invalid command\n", False

#BUY
def handle_buy(tokens, conn):
    if len(tokens) != 7:
        return "403 Message format error\n", False
    _, card_name, card_type, rarity, price_per_card, count, owner_id = tokens
    price_per_card = float(price_per_card)
    count = int(count)
    owner_id = int(owner_id)

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    #does user exist? sufficient balance?
    cursor.execute("SELECT USDBalance FROM Users WHERE ID = ?", (owner_id,))
    user = cursor.fetchone()

    if not user:
        return "404 User does not exist\n", False

    balance = user[0]
    total_price = price_per_card * count

    if balance < total_price:
        return "402 Not enough USD balance\n", False

    #deduct balance, add card to invo
    new_balance = balance - total_price
    cursor.execute("UPDATE Users SET USDBalance = ? WHERE ID = ?", (new_balance, owner_id))
    cursor.execute('''
        INSERT INTO PokemonCards (cardName, cardType, rarity, price, count, ownerID)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (card_name, card_type, rarity, price_per_card, count, owner_id))

    connection.commit()
    connection.close()

    return f"200 OK\nBOUGHT: New balance: {count} {card_name}. User USD balance ${new_balance:.2f}\n", False

#SELL
def handle_sell(tokens, conn):
    if len(tokens) != 5:
        return "403 Message format error\n", False
    _, card_name, count, price_per_card, owner_id = tokens
    count = int(count)
    price_per_card = float(price_per_card)
    owner_id = int(owner_id)

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    #does user exist? does user have card?
    cursor.execute("SELECT ID, count FROM PokemonCards WHERE cardName = ? AND ownerID = ?", (card_name, owner_id))
    card = cursor.fetchone()

    if not card or card[1] < count:
        return "404 Not enough card balance\n", False

    card_id = card[0]
    new_card_count = card[1] - count

    #update user balance, card count
    cursor.execute("UPDATE PokemonCards SET count = ? WHERE ID = ?", (new_card_count, card_id))
    cursor.execute("SELECT USDBalance FROM Users WHERE ID = ?", (owner_id,))
    user_balance = cursor.fetchone()[0]
    new_balance = user_balance + price_per_card * count
    cursor.execute("UPDATE Users SET USDBalance = ? WHERE ID = ?", (new_balance, owner_id))

    connection.commit()
    connection.close()

    return f"200 OK\nSOLD: New balance: {new_card_count} {card_name}. User’s balance USD ${new_balance:.2f}\n", False

#BALANCE
def handle_balance(tokens, conn):
    if len(tokens) != 2:
        return "403 Message format error\n", False

    owner_id = int(tokens[1])

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    #fetch user balance
    cursor.execute("SELECT firstName, lastName, USDBalance FROM Users WHERE ID = ?", (owner_id,))
    user = cursor.fetchone()

    if not user:
        return "404 User does not exist\n", False

    balance_msg = f"Balance for user {user[0]} {user[1]}: ${user[2]:.2f}\n"
    connection.close()

    return f"200 OK\n{balance_msg}", False

#LIST
def handle_list(tokens, conn):
    if len(tokens) != 2:
        return "403 Message format error\n", False

    owner_id = int(tokens[1])

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    #get user's card list
    cursor.execute("SELECT ID, cardName, cardType, rarity, count FROM PokemonCards WHERE ownerID = ?", (owner_id,))
    cards = cursor.fetchall()

    if not cards:
        return "404 No cards found\n", False

    card_list_msg = "\n".join([f"{card[0]} {card[1]} {card[2]} {card[3]} {card[4]}" for card in cards])
    connection.close()

    return f"200 OK\nThe list of records in the Pokémon cards table for current user {owner_id}:\n{card_list_msg}\n", False

#server loop
def run_server():
    init_db()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}...")

    shutdown_flag = False
    while not shutdown_flag:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        data = client_socket.recv(1024).decode('utf-8').strip()
        print(f"Received: {data}")

        response, shutdown_flag = handle_client_command(data, client_socket, client_address)

        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()

    server_socket.close()

if __name__ == "__main__":
    run_server()