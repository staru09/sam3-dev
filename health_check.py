#!/usr/bin/env python3
"""
Simple health check server that responds quickly
Runs alongside the main API to prevent cold start timeouts
"""

import http.server
import socketserver
import threading

PORT = 8081


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logging
        pass


def start_health_server():
    """Start a simple health check server on port 8081"""
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        print(f"Health check server running on port {PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    start_health_server()
