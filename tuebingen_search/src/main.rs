use clap::{Parser, Subcommand};
use scraper::{Html, Selector};
use std::{
    collections::HashMap,
    fs::{self, File},
    io,
    path::{Path, PathBuf},
    time::Instant,
};

#[derive(Parser, Debug)]
#[command(name = "tuebingen-search")]
#[command(version, about = "Small search engine for TÜpedia HTML files")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]

enum Commands {
    Index {
        #[arg(short, long, default_value = "../data/tuepedia/html")]
        dir: String,

        #[arg(short, long, default_value = "index.json")]
        output: String,
    },
    Search {
        #[arg(short, long, default_value = "index.json")]
        index: String,
        #[arg(short, long)]
        query: String,
        #[arg(short, long, default_value_t = 10)]
        top_n: usize,
    },
}

#[derive(Debug)]
struct Tokenizer<'a> {
    content: &'a [char],
}

impl<'a> Tokenizer<'a> {
    fn new(content: &'a [char]) -> Self {
        Self { content }
    }

    fn trim_left(&mut self) {
        while !self.content.is_empty() && self.content[0].is_whitespace() {
            // moves window
            self.content = &self.content[1..]
        }
    }

    fn chop(&mut self, i: usize) -> &'a [char] {
        let token = &self.content[..i];
        self.content = &self.content[i..];
        token
    }

    fn chop_while<P>(&mut self, mut predicate: P) -> &'a [char]
    where
        P: FnMut(&char) -> bool,
    {
        let mut i = 0;

        while i < self.content.len() && predicate(&self.content[i]) {
            i += 1;
        }
        return self.chop(i);
    }

    fn next_token(&mut self) -> Option<String> {
        loop {
            self.trim_left();

            if self.content.is_empty() {
                return None;
            }

            if self.content[0].is_numeric() {
                let token = self.chop_while(|x| x.is_numeric());
                return Some(token.iter().collect::<String>().to_lowercase());
            }

            if self.content[0].is_alphabetic() {
                let token = self.chop_while(|x| x.is_alphanumeric());
                return Some(token.iter().collect::<String>().to_lowercase());
            }

            // ignore punctuation
            self.chop(1);
            continue;
        }
    }
}

impl<'a> Iterator for Tokenizer<'a> {
    type Item = String;

    fn next(&mut self) -> Option<Self::Item> {
        self.next_token()
    }
}

fn extract_text_from_html(file_path: &Path, selector: &Selector) -> io::Result<String> {
    let html = fs::read_to_string(file_path)?;
    let document = Html::parse_document(&html);
    let mut text = String::new();

    for element in document.select(selector) {
        let raw_text = element.text().collect::<Vec<_>>().join(" ");
        let clean_text = raw_text.split_whitespace().collect::<Vec<_>>().join(" ");
        text.push_str(&clean_text);
        text.push(' ');
    }

    return Ok(text);
}
fn main() -> io::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Index { dir, output } => index(&dir, &output)?,
        Commands::Search {
            index,
            query,
            top_n,
        } => search(&index, &query, top_n)?,
    }
    Ok(())
}

fn tokenize(text: &str) -> Vec<String> {
    let chars = text.chars().collect::<Vec<_>>();

    Tokenizer::new(&chars)
        .filter(|term| term.len() >= 2)
        .collect()
}

fn search(index_path: &str, query: &str, top_n: usize) -> io::Result<()> {
    let start = Instant::now();

    let index_file = File::open(index_path)?;
    println!("INFO: Opened file after {:?}", start.elapsed());
    let load_start = Instant::now();

    println!("INFO: Reading {index_path} inverted index.");
    let inverted_index: InvertedIndex = serde_json::from_reader(index_file).expect("TODO");

    println!("INFO: Loaded index after {:?}", load_start.elapsed());

    println!(
        "INFO: {index_path} contains {count_terms} terms.",
        count_terms = inverted_index.len()
    );

    let search_start = Instant::now();

    // prepare query
    let mut query_terms = tokenize(query);
    query_terms.sort();
    query_terms.dedup();

    if query_terms.is_empty() {
        eprintln!("ERROR: No searchable query terms in query.");
        return Ok(());
    }

    println!("INFO: Searching for {query_terms:?} ...");

    let mut scores: HashMap<PathBuf, f64> = HashMap::new();

    for term in query_terms {
        if let Some(postings) = inverted_index.get(&term) {
            for posting in postings {
                *scores.entry(posting.path.clone()).or_insert(0.0) += posting.score;
            }
        }
    }

    let mut results = scores.into_iter().collect::<Vec<_>>();
    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    for (path, score) in results.iter().take(top_n) {
        println!("{score:>8.3} {}", path.display());
    }

    println!("INFO: Search computation took {:?}", search_start.elapsed());
    Ok(())
}

type TermFreq = HashMap<String, usize>;
type TermFreqIndex = HashMap<PathBuf, TermFreq>;
type InverseDocumentIndex = HashMap<String, f64>;
type InvertedIndex = HashMap<String, Vec<Posting>>;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct Posting {
    path: PathBuf,
    score: f64,
}

fn compute_idf(index: &TermFreqIndex) -> InverseDocumentIndex {
    let n = index.len();
    let mut document_frequency: HashMap<String, usize> = HashMap::new();

    for term_frequency in index.values() {
        for term in term_frequency.keys() {
            *document_frequency.entry(term.clone()).or_insert(0) += 1
        }
    }

    document_frequency
        .into_iter()
        .map(|(term, df)| {
            let idf = ((1.0 + n as f64) / (1.0 + df as f64)).ln() + 1.0;
            (term, idf)
        })
        .collect()
}

fn build_inverted_index(term_freq_index: TermFreqIndex) -> InvertedIndex {
    let idf = compute_idf(&term_freq_index);
    let mut inverted_index = InvertedIndex::new();

    for (file_path, term_frequency) in term_freq_index {
        for (term, frequency) in term_frequency {
            let idf_score = idf.get(&term).copied().unwrap_or(0.0);
            let score = idf_score * frequency as f64;

            inverted_index.entry(term).or_default().push(Posting {
                path: file_path.clone(),
                score,
            });
        }
    }

    // pre-ordering of inverted index speeds up search
    for postings in inverted_index.values_mut() {
        postings.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
    }

    inverted_index
}

fn index(dir_path: &str, index_path: &str) -> io::Result<()> {
    let dir = fs::read_dir(dir_path)?;

    let mut term_frequency_index = TermFreqIndex::new();

    let selector = Selector::parse(
        "body h1, body h2, body h3, body h4, \
     body p, body li, body td, body th, \
     body figcaption, body blockquote",
    )
    .unwrap();

    for file in dir {
        let file = file?;

        let file_type = file.file_type()?;
        let file_path = file.path();
        let file_extension = file_path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.eq_ignore_ascii_case("html"))
            .unwrap_or(false);

        if !file_type.is_file() {
            eprintln!("ERROR: Skipped non-file {file:?}", file = file.path());
            continue;
        }

        // crawler might have saved other file extensions, only use html
        if !file_extension {
            eprintln!("ERROR: Skipped non-html file {file:?}", file = file.path());
            continue;
        }

        println!("INFO: Indexing {file_path:?}");

        let text = extract_text_from_html(&file_path, &selector)?;
        let terms = tokenize(&text);

        let mut term_frequency = TermFreq::new();

        for term in terms {
            *term_frequency.entry(term).or_insert(0) += 1;
        }

        term_frequency_index.insert(file_path, term_frequency);
    }

    for (path, tf) in &term_frequency_index {
        println!("INFO: {path:?} has {count} unique tokens", count = tf.len())
    }

    println!("INFO: Computing inverted index...");
    let inverted_index = build_inverted_index(term_frequency_index);

    println!("INFO: Saving {index_path}...");
    let index_file = File::create(index_path)?;
    serde_json::to_writer(index_file, &inverted_index).expect("TODO");

    Ok(())
}
