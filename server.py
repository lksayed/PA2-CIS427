import socket
import sqlite3

import threading
import select

import os

#server config
SERVER_HOST = 'localhost'
SERVER_PORT = 9037
DB_FILE = 'pokemon_trading.db'
MAX_CONNECTIONS = 10

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

#OLD CODE FROM PA1
    # #check for users, if none: create first user
    # cursor.execute("SELECT COUNT(*) FROM Users")
    # user_count = cursor.fetchone()[0]
    # if user_count == 0:
    #     cursor.execute('''
    #         INSERT INTO Users (email, firstName, lastName, userName, password, USDBalance, isRoot)
    #         VALUES ('admin@example.com', 'Admin', 'User', 'admin', 'password', 100.0, 1)
    #     ''')

    #adding in users as defined in direction
    users = [
        ('root', 'Root', 'User', 'Root01', 100.00, 1),
        ('mary', 'Mary', 'Smith', 'mary01', 100.00, 0),
        ('john', 'John', 'Doe', 'john01', 100.00, 0),
        ('moe', 'Moe', 'Howard', 'moe01', 100.00, 0),
    ]
    
    for user in users:
        cursor.execute('''
                       INSERT OR IGNORE INTO Users (email, firstName, lastName, userName, password, USDBalance, isRoot)
                          VALUES (?, ?, ?, ?, ?, ?, ?)
                          ''', user)

    conn.commit()
    conn.close()

#tracking logged in users
logged_in_users = {}

#NEW CLIENT COMMAND HANDLER
def handle_client_command(command, client_address):
    tokens = command.split()
    
    if tokens[0] == 'LOGIN':
        return handle_login(tokens, client_address)
    
    elif tokens[0] == 'LOGOUT':
        return handle_logout(client_address)
    
    elif tokens[0] == 'DEPOSIT':
        return handle_login(tokens, client_address)

    elif tokens[0] == 'WHO':
        return handle_who(client_address)
    
    elif tokens[0] == 'LOOKUP':
        return handle_lookup(tokens, client_address)

    elif tokens[0] == 'LIST':
        return handle_list(tokens, client_address)
        
    elif tokens[0] == 'BUY':
        return handle_buy(tokens, client_address)
    
    elif tokens[0] == 'SELL':
        return handle_sell(tokens, client_address)

    elif tokens[0] == 'BALANCE':
        return handle_balance(tokens, client_address)

    elif tokens[0] == 'SHUTDOWN':
        return handle_shutdown(client_address)

    elif tokens[0] == 'QUIT':
        return handle_quit(client_address)

    else:
        return "400 Invalid command\n", False

#OLD CLIENT COMMAND HANDLER
# #handling user commands
# def handle_client_command(command, conn, address):
#     tokens = command.split()
#     if tokens[0] == 'BUY':
#         return handle_buy(tokens, conn)
#     elif tokens[0] == 'SELL':
#         return handle_sell(tokens, conn)
#     elif tokens[0] == 'BALANCE':
#         return handle_balance(tokens, conn)
#     elif tokens[0] == 'LIST':
#         return handle_list(tokens, conn)
#     elif tokens[0] == 'SHUTDOWN':
#         return "200 OK\n", True
#     elif tokens[0] == 'QUIT':
#         return "200 OK\n", False
#     else:
#         return "400 Invalid command\n", False

#LOGIN
def handle_login(tokens, client_address):
    if len(tokens) != 3:
        return "403 Message format error\n", False
    _, username, password = tokens
    
    #connecting to database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, isRoot FROM Users WHERE userName = ? AND password = ?", (username, password))
    conn.close()
    
    if user:
        user_id, is_root = user
        logged_in_users[client_address] = (user_id, is_root)
        return "200 OK\n", False
    
    else:
        return "403 Invalid username or password\n", False
    
#LOGOUT
def handle_logout(client_address):
    if client_address in logged_in_users:
        del logged_in_users[client_address]
        return "200 OK\n", False
    else:
        return "403 User not logged in\n", False
    
#QUIT
def handle_quit(client_address):
    if client_address in logged_in_users:
        del logged_in_users[client_address]
        print(f"User at {client_address} has logged out and disconnected.")
    
    return "200 OK\nClient connection closed.\n", False

#SHUTDOWN
def handle_shutdown(client_address):
    if client_address not in logged_in_users or logged_in_users[client_address][1] == 0:
        return "401 Unauthorized\n", False
    
    return "200 OK\nShutting down server...\n", True
    
#WHO
def handle_who(client_address):
    if client_address not in logged_in_users or logged_in_users[client_address][1] == 0:
        return "401 Unauthorized\n", False
    
    active_users = "\n".join([f"{user[0]} {address}" for address, user in logged_in_users.items()])
    return f"200 OK\nActive users:\n{active_users}\n", False

#LOOKUP
def handle_lookup(tokens, client_address):
    if client_address not in logged_in_users:
        return "403 Not logged in\n", False
    
    if len(tokens) != 2:
        return "403 Message format error\n", False
    
    search_term = tokens[1]
    user_id, _ = logged_in_users[client_address]
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, cardName, cardType, rarity, price, count FROM PokemonCards WHERE ownerID = ? AND cardName LIKE ?", (user_id, f"%{search_term}%"))
    matches = cursor.fetchall()
    conn.close()
    
    if matches:
        match_list = "\n".join([f"{match[0]} {match[1]} {match[2]} {match[3]} {match[4]}" for match in matches])
        return f"200 OK\nMatches found:\n{match_list}\n", False
    else:
        return "404 No matches found\n", False

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

#NEW LIST FUNCTION
def handle_list(tokens, client_address):
    if client_address not in logged_in_users:
        return "403 Not logged in\n", False
    
    user_id, is_root = logged_in_users[client_address]
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if is_root:
        cursor.execute("SELECT ID, cardName, cardType, rarity, count, ownerID FROM PokemonCards")
    
    else:
        cursor.execute("SELECT ID, cardName, cardType, rarity, count FROM PokemonCards WHERE ownerID = ?", (user_id,))
    
    cards = cursor.fetchall()
    conn.close()
    
    if cards:
        card_list = "\n".join([f"{card[0]} {card[1]} {card[2]} {card[3]} {card[4]}" for card in cards])
        return f"200 OK\nCards:\n{card_list}\n", False
    
    else:
        return "404 No cards found\n", False

# OLD LIST FUNCTION
# def handle_list(tokens, conn):
#     if len(tokens) != 2:
#         return "403 Message format error\n", False

#     owner_id = int(tokens[1])

#     connection = sqlite3.connect(DB_FILE)
#     cursor = connection.cursor()

#     #get user's card list
#     cursor.execute("SELECT ID, cardName, cardType, rarity, count FROM PokemonCards WHERE ownerID = ?", (owner_id,))
#     cards = cursor.fetchall()

#     if not cards:
#         return "404 No cards found\n", False

#     card_list_msg = "\n".join([f"{card[0]} {card[1]} {card[2]} {card[3]} {card[4]}" for card in cards])
#     connection.close()

#     return f"200 OK\nThe list of records in the Pokémon cards table for current user {owner_id}:\n{card_list_msg}\n", False

#new client handler
def client_handler(client_socket, client_address):
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8').strip()
            
            if not data:
                break
            
            print(f"Received: {data} from {client_address}")
            
            response, shutdown_flag = handle_client_command(data, client_address)
            
            client_socket.sendall(response.encode('utf-8'))
            
            if shutdown_flag:
                print("Shutting down server...")
                os._exit(0)
                
            if data.startswith("QUIT"):
                break
            
    except Exception as e:
        print(f"An error occurred: {e} while handling client at {client_address}")
        
    finally:
        client_socket.close()
        print(f"{client_address}'s connection closed.")

#server loop
def run_server():
    init_db()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}...")

    sockets_list = [server_socket]
    client_sockets = {}
    
    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)
        
        for notified_socket in read_sockets:
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address} accepted")
                
                sockets_list.append(client_socket)
                client_sockets[client_socket] = client_address
                
            else:
                client_thread = threading.Thread(target=client_handler, args=(notified_socket, client_sockets[notified_socket]))
                client_thread.start()
                
                sockets_list.remove(notified_socket)
                del client_sockets[notified_socket]
        
        for notified_socket in exception_sockets:
            sockets_list.remove(notified_socket)
            if notified_socket in client_sockets:
                del client_sockets[notified_socket]

if __name__ == "__main__":
    run_server()