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

    #adding in users as defined in direction
    users = [
        ('emailroot@ex.com', 'Root', 'User', 'root', 'Root01', 100.00, 1),
        ('emailmary@ex.com', 'Mary', 'Smith', 'mary', 'mary01', 100.00, 0),
        ('emailjohn@ex.com', 'John', 'Doe', 'john', 'john01', 100.00, 0),
        ('emailmoe@ex.com', 'Moe', 'Howard', 'moe', 'moe01', 100.00, 0),
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
        return handle_deposit(tokens, client_address)

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

#LOGIN
def handle_login(tokens, client_address):
    if len(tokens) != 3:
        return "403 Message format error\n", False
    _, username, password = tokens

    # connect to the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, isRoot FROM Users WHERE userName = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_id, is_root = user

        # debugging
        print(f"LOGIN Command: User {username} ({user_id}) logged in from {client_address}. Root: {is_root}")

        # add client address to the logged_in_users
        if user_id not in logged_in_users:
            logged_in_users[user_id] = (is_root, [client_address])
        else:
            if client_address not in logged_in_users[user_id][1]:
                logged_in_users[user_id][1].append(client_address)

        return "200 OK\n", False
    else:
        return "403 Invalid username or password\n", False
  
#LOGOUT
def handle_logout(client_address):
    # find userID associated with client address
    for user_id, (is_root, addresses) in list(logged_in_users.items()):
        if client_address in addresses:
            # remove the client address from list of addresses
            addresses.remove(client_address)
            
            # if no addresses left, remove user from logged_in_users
            if not addresses:
                del logged_in_users[user_id]
            
            print(f"User at {client_address} has logged out.")
            return "200 OK\n", False
    
    # if client address not found
    return "403 User not logged in\n", False  
    
#QUIT
def handle_quit(client_address):
    if client_address in logged_in_users:
        del logged_in_users[client_address]
        print(f"User at {client_address} has logged out and disconnected.")
    
    return "200 OK\nClient connection closed.\n", False

#SHUTDOWN
def handle_shutdown(client_address):
    # check if client is logged in and is root
    for user_id, (is_root, addresses) in logged_in_users.items():
        if client_address in addresses:
            if is_root != 1:  # user is not root
                return "401 Unauthorized\n", False

            # if root user, proceed
            print("Shutdown command received from root user.")
            return "200 OK\nShutting down server...\n", True

    # if client not logged in
    return "403 Not logged in\n", False
    
#WHO
def handle_who(client_address):
    # check if client is logged in
    for user_id, (is_root, addresses) in logged_in_users.items():
        if client_address in addresses:
            # if user logged in, check if root
            if is_root != 1:  # not root
                return "401 Unauthorized\n", False

            # prepare list of active users
            active_users = "\n".join([
                f"UserID: {uid} | IPs: {', '.join(map(str, addrs))}" 
                for uid, (_, addrs) in logged_in_users.items()
            ])
            return f"200 OK\nActive users:\n{active_users}\n", False

    # if client is not logged in
    return "403 Not logged in\n", False

#LOOKUP
def handle_lookup(tokens, client_address):
    # iterate through logged_in_users and find client_address
    for user_id, (is_root, addresses) in logged_in_users.items():
        if client_address in addresses:
            # check command format is correct
            if len(tokens) != 2:
                return "403 Message format error\n", False

            search_term = tokens[1]

            # check database for matching cards owned by logged-in user
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ID, cardName, cardType, rarity, price, count FROM PokemonCards WHERE ownerID = ? AND cardName LIKE ?",
                (user_id, f"%{search_term}%")
            )
            matches = cursor.fetchall()
            conn.close()

            if matches:
                match_list = "\n".join([f"{match[0]} {match[1]} {match[2]} {match[3]} {match[4]} {match[5]}" for match in matches])
                return f"200 OK\nMatches found:\n{match_list}\n", False
            else:
                return "404 No matches found\n", False

    # if client address is not found, return not logged in
    return "403 Not logged in\n", False

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

#DEPOSIT
def handle_deposit(tokens, client_address):
    # iterate through logged_in_users and find client_address
    for user_id, (is_root, addresses) in logged_in_users.items():
        if client_address in addresses:
            # check command format is correct
            if len(tokens) != 2:
                return "403 Message format error\n", False

            try:
                deposit_amount = float(tokens[1])
            except ValueError:
                return "403 Invalid deposit amount\n", False

            # update user's balance in the database
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET USDBalance = USDBalance + ? WHERE ID = ?", (deposit_amount, user_id))
            conn.commit()

            # confirm new balance
            cursor.execute("SELECT USDBalance FROM Users WHERE ID = ?", (user_id,))
            new_balance = cursor.fetchone()[0]
            conn.close()

            return f"200 OK\nDeposited ${deposit_amount:.2f}. New balance: ${new_balance:.2f}\n", False

    # otherwise, if user not logged in
    return "403 Not logged in\n", False

#SELL
def handle_sell(tokens, client_address):
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
def handle_balance(tokens, client_address):
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
    # check if client logged in
    for user_id, (is_root, addresses) in logged_in_users.items():
        if client_address in addresses:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # root user can see all cards
            if is_root:
                cursor.execute("SELECT ID, cardName, cardType, rarity, count, ownerID FROM PokemonCards")
            else:
                # regular users only see own cards
                cursor.execute("SELECT ID, cardName, cardType, rarity, count FROM PokemonCards WHERE ownerID = ?", (user_id,))

            cards = cursor.fetchall()
            conn.close()

            if cards:
                card_list = "\n".join([f"{card[0]} {card[1]} {card[2]} {card[3]} {card[4]}" for card in cards])
                return f"200 OK\nCards:\n{card_list}\n", False
            else:
                return "404 No cards found\n", False

    # if client not logged in
    return "403 Not logged in\n", False

#new client handler
def client_handler(client_socket, client_address):
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8').strip()
            
            if not data:
                break
            
            print(f"Received: {data} from {client_address}")
            
            # process command
            response, shutdown_flag = handle_client_command(data, client_address)
            
            # send server's response
            client_socket.sendall(response.encode('utf-8'))
            
            # handle shutdown
            if shutdown_flag:  # For SHUTDOWN command
                print("Shutting down server...")
                os._exit(0)
            
            # client sends QUIT, terminate session
            if data.startswith("QUIT"):
                print(f"User at {client_address} has disconnected.")
                break

    except Exception as e:
        print(f"An error occurred: {e} while handling client at {client_address}")

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