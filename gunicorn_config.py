import multiprocessing

# Server socket
bind = "0.0.0.0:8080"

# Worker processes - Reduced to prevent memory issues
workers = 1  # Single worker to prevent memory issues
worker_class = "sync"

# Timeouts - Increased for slow Firecrawl requests
timeout = 600  # 10 minutes
keepalive = 5
graceful_timeout = 600  # 10 minutes for graceful shutdown

# Memory management
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance
max_requests = 50  # Restart worker after 50 requests to prevent memory leaks
max_requests_jitter = 10  # Add some randomness to prevent all workers restarting at once

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Worker settings
preload_app = True  # Preload application to reduce startup time
worker_connections = 100

# Memory limits
worker_max_memory_percent = 70  # Restart worker if memory usage exceeds 70%
worker_max_memory_usage = 128  # Maximum memory per worker in MB 