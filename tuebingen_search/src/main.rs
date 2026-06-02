use scraper::{Html, Selector};
use std::{collections::HashMap, fs::{self, File}, io, path::PathBuf};

#[derive(Debug)]
struct Lexer<'a> {
    content: &'a [char],
}

impl<'a> Lexer<'a> {
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

    fn chop_while<P>(&mut self, mut predicate: P) -> &'a [char] where P: FnMut(&char) -> bool {
        let mut i = 0;

        while i < self.content.len() && predicate(&self.content[i]) {
            i += 1;
        }
        return self.chop(i);
    }

    fn next_token(&mut self) -> Option<&'a [char]> {
        loop {
            self.trim_left();

            if self.content.is_empty() {
                return None;
            }

            if self.content[0].is_numeric() {
                return Some(self.chop_while(|x| x.is_numeric()));
            }

            if self.content[0].is_alphabetic() {
                return Some(self.chop_while(|x| x.is_alphanumeric()));
            }

            // ignore punctuation
            return Some(self.chop(1));
            //self.content = &self.content[1..];
        }
    }
}

impl<'a> Iterator for Lexer<'a> {
    type Item = &'a [char];

    fn next(&mut self) -> Option<Self::Item> {
        self.next_token()
    }
}

fn extract_text_from_html(file_path_buffer: &PathBuf) -> io::Result<String> {
    let file_path = file_path_buffer.to_str().expect("TODO");
    let html = fs::read_to_string(file_path)?;
    let document = Html::parse_document(&html);

    let selector = Selector::parse(
        "body h1, body h2, body h3, body h4, \
     body p, body li, body td, body th, \
     body figcaption, body blockquote",
    )
    .unwrap();

    let mut text = String::new();
    for element in document.select(&selector) {
        let raw_text = element.text().collect::<Vec<_>>().join(" ");
        let clean_text = raw_text.split_whitespace().collect::<Vec<_>>().join(" ");
        text.push_str(&clean_text);
        text.push(' ');
    }

    return Ok(text);
}
type TermFreq = HashMap::<String, usize>;
type TermFreqIndex = HashMap::<PathBuf, TermFreq>;

fn main() -> io::Result<()> {
    let index_path = "index.json";
    let index_file = File::open(index_path)?;
    println!("Reading {index_path} index file");
    let term_freqency_index: TermFreqIndex = serde_json::from_reader(index_file).expect("TODO");
    println!("{index_path} contains {count_files}", count_files = term_freqency_index.len());
    
    Ok(())
}

fn main2() -> io::Result<()> {
    let dir_path = "../data/tuepedia/html";
    let dir = fs::read_dir(dir_path)?;
    
    let mut term_frequency_index = TermFreqIndex::new();

    for file in dir {
        let file_path = file?.path();

        println!("Indexing {file_path:?}");
        
        let content = extract_text_from_html(&file_path)?
        .chars()
        .collect::<Vec<_>>();


        let mut term_frequency = TermFreq::new();

        for token in Lexer::new(&content) {
            let term = token.iter().map(|x| x.to_ascii_lowercase()).collect::<String>();
            
            if let Some(freq) = term_frequency.get_mut(&term) {
                *freq += 1;
            } else {
                term_frequency.insert(term, 1);
            }
        }

        let mut stats = term_frequency.iter().collect::<Vec<_>>();
        stats.sort_by_key(|(_, freq)| *freq);
        stats.reverse();

        term_frequency_index.insert(file_path, term_frequency);
    }

    for (path, tf) in &term_frequency_index {
        println!("{path:?} has {count} unique tokens", count = tf.len())
    }

    let index_path = "index.json";
    println!("Saving {index_path} ...");
    let index_file = File::create(index_path)?;
    serde_json::to_writer(index_file, &term_frequency_index).expect("TODO");

    Ok(())
}
