# This file is for you! Edit it to implement your own hooks (make targets) into
# the project as automated steps to be executed on locally and in the CD pipeline.

include scripts/init.mk

# ==============================================================================

# Example CI/CD targets are: dependencies, build, publish, deploy, clean, etc.

dependencies: # Install dependencies needed to build and test the project @Pipeline
	make \
		install-root-project

config:: # Configure development environment (main) @Configuration
	make \
		python-install \
		terraform-install

install-poetry:
	curl -sSL https://install.python-poetry.org | python3.9 -
	echo 'export PATH="$$HOME/.local/bin:$$PATH"' >> ~/.bashrc
	source ~/.bashrc

setup:
	sudo add-apt-repository ppa:deadsnakes/ppa
	sudo apt install python3.9
	sudo apt install python3.9-venv python3-venv

install-root-project:
	${MAKE} install-poetry
	python3.9 -m venv .venv
	source .venv/bin/activate
	poetry install --no-root --with dev


# ==============================================================================

${VERBOSE}.SILENT: \
	config \
	dependencies \
