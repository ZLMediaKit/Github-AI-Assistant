#!/bin/bash
if ! grep -qi "ubuntu" /etc/os-release; then
    echo "The current OS is not Ubuntu. Please activate the virtual environment first."
    python main.py "$@"
    exit 0
fi


if ! [ -x "$(command -v python3.11)" ]; then
    echo "Python 3.11 is not installed. Installing Python 3.11..."
    sudo -v
    sudo apt update
    sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev \
    libffi-dev libsqlite3-dev wget libbz2-dev liblzma-dev -y
    sudo apt install python3.11 python3.11-dev python3.11-venv -y
fi


if ! [ -x "$(command -v python3.11)" ]; then
    echo "Python 3.11 is not installed. Installing Python 3.11 using ppa:deadsnakes/ppa..."
    sudo -v
    sudo apt update
    sudo apt install software-properties-common -y
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install python3.11 python3.11-dev python3.11-venv -y
fi

if ! [ -x "$(command -v python3.11)" ]; then
    echo "Python 3.11 is not installed. Please install Python 3.11 manually."
    exit 1
fi

if [ ! -d "venv" ] || ! python3.11 -c "import sys; print(sys.version)" | grep -q "^3.11"; then
    echo "Creating Python 3.11 virtual environment..."
    sudo -v
    sudo apt update
    sudo apt install build-essential swig libpcre3-dev libpcre3 git -y
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if virtual environment is activated successfully, if not, exit. Check method: check whether the python version is 3.11.6
if ! python -c "import sys; print(sys.version)" | grep -q "^3.11"; then
    echo "Python 3.11 virtual environment is not activated. Please activate it manually."
    exit 1
fi

# Check if typer is installed, if not install it
pip list > /tmp/pip_list_output
if ! grep -q 'typer' /tmp/pip_list_output; then
    echo "Installing typer..."
    pip install "typer[all]==0.9.0"
fi
rm /tmp/pip_list_output

python main.py "$@"
