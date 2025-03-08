FROM ros:foxy

# Install required ROS packages and web server
RUN apt-get update && apt-get install -y \
    ros-${ROS_DISTRO}-rosbridge-server \
    nginx \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install roslibjs dependencies
RUN pip3 install tornado

# Create web directory
WORKDIR /var/www/html

# Copy web files
COPY ./web /var/www/html/

# Configure nginx
RUN echo "server {\n\
    listen 9999;\n\
    server_name localhost;\n\
    root /var/www/html;\n\
    index index.html;\n\
    location / {\n\
        try_files \$uri \$uri/ =404;\n\
    }\n\
}" > /etc/nginx/sites-available/ros_web && \
    ln -s /etc/nginx/sites-available/ros_web /etc/nginx/sites-enabled/ && \
    rm /etc/nginx/sites-enabled/default

# Copy entrypoint script
COPY ./entrypoint.sh /

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Expose the web port and rosbridge port
EXPOSE 9999 9090

ENTRYPOINT ["/entrypoint.sh"] 