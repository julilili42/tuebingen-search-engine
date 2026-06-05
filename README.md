# Tübingen Search Engine

> A custom search engine with link crawling and an indexing pipeline — built to explore how search systems collect, process and rank web content.

## Status

🚧 Work in Progress

This project is currently under development.  
The core goal is to build a small but understandable search engine from scratch: crawler, parser, indexer and ranking layer.

## Why I built this

Modern search engines feel simple from the outside, but are complex systems internally.  
This project is my attempt to break the problem down into smaller parts and implement the core ideas myself.

## Current Features

- Link crawler for discovering pages
- Basic URL queue handling
- HTML content extraction
- Indexing pipeline for collected pages
- Search endpoint / query interface
- Early ranking logic

## Planned Features

- Better ranking algorithm
- Duplicate detection
- Crawl depth control
- Robots.txt handling
- Frontend search UI
- Result snippets
- Performance benchmarks
- Unit tests for crawler and indexer

## Architecture

```text
Seed URLs
   ↓
Crawler
   ↓
HTML Parser
   ↓
Content Cleaner
   ↓
Indexer
   ↓
Search / Ranking
   ↓
Results UI