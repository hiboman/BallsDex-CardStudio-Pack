# BallsDex CardStudio Package

A card customization package for **BallsDex**.

## Installation

### 1 — Configure extra.toml

**If the file doesn't exist:** Create a new file `extra.toml` in your `config` folder under the BallsDex directory.

**If you already have other packages installed:** Simply add the following configuration to your existing `extra.toml` file. Each package is defined by a `[[ballsdex.packages]]` section, so you can have multiple packages installed.

Add the following configuration:

```toml
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-CardStudio-Pack.git@0.0.2#master"
path = "cardstudio"
enabled = true
```

**Example of multiple packages:**

```toml
# First package
[[ballsdex.packages]]
location = "git+https://github.com/example/other-package.git"
path = "other"
enabled = true

# Achievements Package
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-CardStudio-Pack.git@0.0.2#master"
path = "cardstudio"
enabled = true
```

### 2 — Rebuild and start the bot

```bash
docker compose build
docker compose up -d
```

This will install the package and start the bot.
