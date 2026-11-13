---
title: 'WP-CLI Tips: Search & Replace Like a Pro'
date: '2025-11-03'
type: article
categories:
- knowledge-sharing
tags:
- Application Migration
- docker
- php
- wordpress
summary: 'If you run a WordPress website or manage multiple WordPress instances, sooner or later you’ll face a classic problem: You move your site from an IP-based environment or staging domain to a real domain — and suddenly…'
---

If you run a WordPress website or manage multiple WordPress instances, sooner or later you’ll face a classic problem:

> **You move your site from an IP-based environment or staging domain to a real domain — and suddenly your internal links, media URLs, and pingbacks still point to the old host.**

Manually rewriting database values?  
*Painful.*

Exporting SQL and hunting down strings?  
*Error-prone and slow.*

A much faster and safer way is to use **WP-CLI** — a powerful command-line tool for WordPress administration.

Below is a practical snippet I recently used when migrating a WordPress instance from an IP-based dev server to a production domain.

## Install WP-CLI and perform safe domain replacement

```
apt update && apt install wget -y

wget https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
mv wp-cli.phar /usr/local/bin/wp

wp --version --allow-root

OLD_IP="http://192.168.1.10:8082/"
NEW_HOST="https://newdomain.com"

# First: dry-run — preview changes without modifying data
wp search-replace "$OLD_IP" "$NEW_HOST" \
  --all-tables --precise --recurse-objects --dry-run --allow-root

# Then: actual replacement
wp search-replace "$OLD_IP" "$NEW_HOST" \
  --all-tables --precise --recurse-objects --allow-root
```

## What this does

This script:

1. Installs WP-CLI
2. Checks its version
3. Defines old and new host URLs
4. Runs a **dry run first** (so you can inspect changes safely)
5. Executes precise search-and-replace across all database tables

This method updates:

- WordPress content
- Media URLs
- Serialized arrays and objects (important!)
- Internal links and pingbacks
- Any other references to your old host/IP

### Note *(–allow-root)*

In this example, I ran WP-CLI inside a Docker WordPress container, which is why the command includes –allow-root. Inside containers, WordPress commonly runs as root, so it’s normal.

However, on a normal server **do not run WordPress commands as root** — use the correct site user instead.

## Why WP-CLI is better than manual SQL edits

WP-CLI:

- Correctly handles serialized data (SQL search-replace usually breaks it)
- Is much faster than phpMyAdmin edits
- Lets you preview changes before applying
- Works across all tables, including plugin data

Even better — this trick isn’t only for domain migration.

You can use WP-CLI to safely replace **any content** in your WordPress database: links, media paths, shortcodes, CDN URLs, etc.

### If you maintain WordPress long-term — install WP-CLI

It’s one of the most essential tools for WordPress engineers, especially for:

- Migrations
- CI/CD environments
- Large content updates
- Dev → staging → production workflows
