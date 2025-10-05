FROM python:3.11-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    freeglut3-dev \
    mesa-common-dev \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set up a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Switch to the non-root user
USER $USERNAME
