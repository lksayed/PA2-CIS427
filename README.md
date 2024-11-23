# Programming Assignment 2 - CIS427 - Pokemon Card Trading Server/Client
### Tools Needed:
+ Python
+ Terminal
+ Visual Studio Code

### Set-Up Instructions:
1. Ensure that the most recent version of Python is downloaded and installed on your computer

### Running the Program
1. Open Terminal and run these commands:

    a. cd into the folder containing the project code

    b. start server: 'python3 server.py' 

    c. start client: 'python3 client.py localhost 9037'

    d. All set!

### Command Implementations
1. LOGIN:
     > Format: LOGIN <userName> <password>
     > Function Definition: Upon launch of the server, user must login to access any functions.
     
     > 200 OK if LOGIN credentials are correct and user will be logged into their correct account; 403 if incorrect format; 401 if unauthorized.

2. LOGOUT:
    > Format: LOGOUT
    > Function Definition: Logs the current user out of their session.

3. BUY
     > Format: BUY <cardName> <cardType> <rarity> <price> <count> <ownerID>
     > Function Definition: Upon launch of the server, a database with two tables (Users & Cards) will be created.

     > Users table will have a single user to start and balance will default to $100.
     
     > 200 OK if BUY is within parameters and will add the purchased card to Cards table; 403 if message format is incorrect; 404 if not enough balance to purchase.

4. SELL
     > Format: SELL <count> <price> <ownerID>
     > Function Definition: Allows user to sell a card listed in their inventory
     
     > 200 OK if SELL is within parameters and will remove the quantity of sold card(s) from Cards table; 403 if message format is incorrect; 404 if card is not available to be sold.

5. LIST
     > Format: LIST <ownerID>
     > Function Definition: Lists all cards that are currently contained in Users inventory.

6. BALANCE
     > Format: BALANCE <ownerID>
     > Function Definition: Provides the Users monetary balance.

7. DEPOSIT:
    > Format: DEPOSIT <amount>
    > Function Definition: Deposits set amount of money into the current user logged in.

8. LOOKUP:
    > Format: LOOKUP <term>
    > Function Definition: Returns cards within database that match search term.

9. WHO:
    > Format: WHO
    > Function Definition: Returns a list of users currently logged in with their names and IP addresses.

    > Limited to Root user only.

10. SHUTDOWN: 
        > Format: SHUTDOWN
        > Function Definition: Quits the program entirely by shutting down the server and closing the client-side. 
        
        > Limited to Root user only.

. QUIT: Quits the program by closing the client-side.

### Known Project Deficiencies
1. None to my knowledge.

### Test Cases:
| **Test #** | **Description of Test**            | **Input Value**                             | **Expected Output**                                             | **Pass/Fail** |
|------------|------------------------------------|---------------------------------------------|-----------------------------------------------------------------|---------------|
| 1          | Successful login                  | `LOGIN root Root01`                         | `200 OK`                                                        | Pass/Fail     |
| 2          | Failed login (wrong password)     | `LOGIN root WrongPassword`                  | `403 Invalid username or password`                              | Pass/Fail     |
| 3          | Failed login (missing fields)     | `LOGIN root`                                | `403 Message format error`                                      | Pass/Fail     |
| 4          | Successful logout                 | `LOGOUT`                                    | `200 OK`                                                        | Pass/Fail     |
| 5          | Logout without login              | `LOGOUT`                                    | `403 User not logged in`                                        | Pass/Fail     |
| 6          | Successful deposit                | `DEPOSIT 50`                                | `200 OK\nDeposited $50.00. New balance: $150.00`                | Pass/Fail     |
| 7          | Deposit without login             | `DEPOSIT 50`                                | `403 Not logged in`                                             | Pass/Fail     |
| 8          | Deposit with invalid format       | `DEPOSIT`                                   | `403 Message format error`                                      | Pass/Fail     |
| 9          | List cards (regular user)         | `LIST`                                      | `200 OK\nList of records in Pokémon cards for current user.`    | Pass/Fail     |
| 10         | List all cards (root user)        | `LIST`                                      | `200 OK\nList of all Pokémon cards in the database.`            | Pass/Fail     |
| 11         | List cards without login          | `LIST`                                      | `403 Not logged in`                                             | Pass/Fail     |
| 12         | Successful lookup (partial match) | `LOOKUP Pikachu`                            | `200 OK\nMatches found:\n<ID> Pikachu Electric Common $[Price]` | Pass/Fail     |
| 13         | Lookup with no match              | `LOOKUP RandomCard`                         | `404 No matches found`                                          | Pass/Fail     |
| 14         | Lookup without login              | `LOOKUP Pikachu`                            | `403 Not logged in`                                             | Pass/Fail     |
| 15         | Successful buy                    | `BUY Charizard Fire Rare 50 2 2`            | `200 OK\nBOUGHT: New balance: $[NewBalance].`                   | Pass/Fail     |
| 16         | Buy with insufficient balance     | `BUY Charizard Fire Rare 5000 2 2`          | `402 Not enough USD balance`                                    | Pass/Fail     |
| 17         | Successful sell                   | `SELL Charizard 2 50 2`                     | `200 OK\nSOLD: New balance: $[NewBalance].`                     | Pass/Fail     |
| 18         | Check balance                     | `BALANCE 1`                                 | `200 OK\nBalance for user: $[Balance]`                          | Pass/Fail     |
| 19         | Check balance without login       | `BALANCE 1`                                 | `403 Not logged in`                                             | Pass/Fail     |
| 20         | WHO command (root user)           | `WHO`                                       | `200 OK\nActive users:\n<Username> <IP>`                        | Pass/Fail     |
| 21         | WHO command (non-root user)       | `WHO`                                       | `401 Unauthorized`                                              | Pass/Fail     |
| 22         | Shutdown (root user)              | `SHUTDOWN`                                  | `200 OK\nShutting down server...`                               | Pass/Fail     |
| 23         | Shutdown (non-root user)          | `SHUTDOWN`                                  | `401 Unauthorized`                                              | Pass/Fail     |
| 24         | Quit session                      | `QUIT`                                      | `200 OK\nClient connection closed.`                             | Pass/Fail     |