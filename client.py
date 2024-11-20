import socket
import sys

#client config
def run_client(server_host, server_port):
    logged_in = False
    
    while True:
        #prompt user to enter command
        command = input("Enter command (LOGIN, LOGOUT, BUY, SELL, BALANCE, LIST, DEPOSIT, WHO, LOOKUP, SHUTDOWN, QUIT): ").strip()

        if not command:
            continue
        
        if not logged_in and not command.startswith("LOGIN") and not command.startswith("QUIT"):
            print("Please login first.")
            continue

        #connect to server
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_host, server_port))

            #send command to server
            client_socket.sendall(command.encode('utf-8'))

            #receive server response
            response = client_socket.recv(1024).decode('utf-8')
            print(f"Server response: {response}")

            if command.startswith("LOGIN") and "200 OK" in response:
                logged_in = True
                
            elif command.startswith("LOGOUT") and "200 OK" in response:
                logged_in = False
                
            elif command.startswith("QUIT") or command.startswith("SHUTDOWN"):
                print("Closing client.")
                break

        except ConnectionRefusedError:
            print("Failed to connect to server. Please check if the server is running.")
            break
        
        except Exception as e:
            print(f"An error occurred: {e}")
            break

        finally:
            client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py <SERVER_HOST> <SERVER_PORT>")
        sys.exit(1)

    server_host = sys.argv[1]
    server_port = int(sys.argv[2])

    run_client(server_host, server_port)