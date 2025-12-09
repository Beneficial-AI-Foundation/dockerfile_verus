//! Verus function parser using verus_syn
//!
//! This tool parses Verus/Rust code to extract function information,
//! replacing the adhoc regex-based approach in find_verus_functions.py

use clap::{Parser, ValueEnum};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use verus_syn::spanned::Spanned;
use verus_syn::visit::Visit;
use verus_syn::{ImplItemFn, Item, ItemFn, ItemMacro, TraitItemFn, Visibility};
use walkdir::WalkDir;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to search (file or directory)
    #[arg(value_name = "PATH")]
    path: PathBuf,

    /// Output format
    #[arg(short, long, value_enum, default_value = "json")]
    format: OutputFormat,

    /// Include Verus-specific constructs (spec, proof, exec functions)
    #[arg(long, default_value = "true")]
    include_verus_constructs: bool,

    /// Include trait and impl method functions
    #[arg(long, default_value = "true")]
    include_methods: bool,

    /// Show function visibility (pub/private)
    #[arg(long)]
    show_visibility: bool,

    /// Show function kind (fn, spec fn, proof fn, exec fn, const fn)
    #[arg(long)]
    show_kind: bool,
}

#[derive(Debug, Clone, ValueEnum)]
enum OutputFormat {
    Json,
    Text,
    Detailed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FunctionInfo {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    file: Option<String>,
    start_line: usize,
    end_line: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    visibility: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    context: Option<String>, // "impl", "trait", or "standalone"
}

#[derive(Debug, Serialize, Deserialize)]
struct ParsedOutput {
    functions: Vec<FunctionInfo>,
    functions_by_file: HashMap<String, Vec<FunctionInfo>>,
    summary: Summary,
}

#[derive(Debug, Serialize, Deserialize)]
struct Summary {
    total_functions: usize,
    total_files: usize,
}

/// Visitor that collects function information from an AST
struct FunctionVisitor {
    functions: Vec<FunctionInfo>,
    file_path: Option<String>,
    include_verus_constructs: bool,
    include_methods: bool,
    show_visibility: bool,
    show_kind: bool,
}

impl FunctionVisitor {
    fn new(
        file_path: Option<String>,
        include_verus_constructs: bool,
        include_methods: bool,
        show_visibility: bool,
        show_kind: bool,
    ) -> Self {
        Self {
            functions: Vec::new(),
            file_path,
            include_verus_constructs,
            include_methods,
            show_visibility,
            show_kind,
        }
    }

    fn extract_function_kind(&self, sig: &verus_syn::Signature) -> String {
        // Check for Verus-specific function modes
        // Note: In verus_syn, mode is FnMode enum, not Option<FnMode>
        use verus_syn::FnMode;
        
        let mode_str = match sig.mode {
            FnMode::Spec(_) => "spec",
            FnMode::SpecChecked(_) => "spec(checked)",
            FnMode::Proof(_) => "proof", 
            FnMode::ProofAxiom(_) => "proof(axiom)",
            FnMode::Exec(_) => "exec",
            FnMode::Default => "",
        };
        
        if sig.constness.is_some() {
            if mode_str.is_empty() {
                "const fn".to_string()
            } else {
                format!("{} const fn", mode_str)
            }
        } else if !mode_str.is_empty() {
            format!("{} fn", mode_str)
        } else {
            "fn".to_string()
        }
    }

    fn extract_visibility(&self, vis: &Visibility) -> String {
        match vis {
            Visibility::Public(_) => "pub".to_string(),
            Visibility::Restricted(r) => {
                // pub(crate), pub(super), etc.
                // Convert path to string - check if it's a simple identifier
                if r.path.segments.len() == 1 {
                    let seg = &r.path.segments[0];
                    format!("pub({})", seg.ident)
                } else {
                    // For complex paths, just use a generic label
                    "pub(restricted)".to_string()
                }
            }
            Visibility::Inherited => "private".to_string(),
        }
    }

    fn should_include_function(&self, sig: &verus_syn::Signature) -> bool {
        if self.include_verus_constructs {
            true
        } else {
            // Exclude Verus-specific modes (spec, proof, exec)
            use verus_syn::FnMode;
            matches!(sig.mode, FnMode::Default)
        }
    }

    fn add_function(
        &mut self,
        name: String,
        span: proc_macro2::Span,
        sig: &verus_syn::Signature,
        vis: &Visibility,
        context: Option<String>,
    ) {
        if !self.should_include_function(sig) {
            return;
        }

        let kind = if self.show_kind {
            Some(self.extract_function_kind(sig))
        } else {
            None
        };

        let visibility = if self.show_visibility {
            Some(self.extract_visibility(vis))
        } else {
            None
        };

        self.functions.push(FunctionInfo {
            name,
            file: self.file_path.clone(),
            start_line: span.start().line,
            end_line: span.end().line,
            kind,
            visibility,
            context,
        });
    }
}

impl<'ast> Visit<'ast> for FunctionVisitor {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        let name = node.sig.ident.to_string();
        let span = node.span();
        self.add_function(name, span, &node.sig, &node.vis, Some("standalone".to_string()));

        // Continue visiting nested items
        verus_syn::visit::visit_item_fn(self, node);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        if !self.include_methods {
            return;
        }

        let name = node.sig.ident.to_string();
        let span = node.span();
        self.add_function(name, span, &node.sig, &node.vis, Some("impl".to_string()));

        // Continue visiting nested items
        verus_syn::visit::visit_impl_item_fn(self, node);
    }

    fn visit_trait_item_fn(&mut self, node: &'ast TraitItemFn) {
        if !self.include_methods {
            return;
        }

        let name = node.sig.ident.to_string();
        let span = node.span();
        
        // Trait items don't have explicit visibility (they inherit from trait)
        let vis = Visibility::Inherited;
        self.add_function(name, span, &node.sig, &vis, Some("trait".to_string()));

        // Continue visiting nested items
        verus_syn::visit::visit_trait_item_fn(self, node);
    }

    fn visit_item_impl(&mut self, node: &'ast verus_syn::ItemImpl) {
        verus_syn::visit::visit_item_impl(self, node);
    }

    fn visit_item_trait(&mut self, node: &'ast verus_syn::ItemTrait) {
        verus_syn::visit::visit_item_trait(self, node);
    }

    fn visit_item_mod(&mut self, node: &'ast verus_syn::ItemMod) {
        verus_syn::visit::visit_item_mod(self, node);
    }

    fn visit_item_macro(&mut self, node: &'ast ItemMacro) {
        if let Some(ident) = &node.mac.path.get_ident() {
            if *ident == "verus" {
                // Parse verus! macro body as items
                if let Ok(items) = verus_syn::parse2::<VerusMacroBody>(node.mac.tokens.clone()) {
                    for item in items.items {
                        self.visit_item(&item);
                    }
                }
            } else if *ident == "cfg_if" {
                // Parse cfg_if! macro body
                if let Ok(branches) = verus_syn::parse2::<CfgIfMacroBody>(node.mac.tokens.clone())
                {
                    for items in branches.all_items {
                        for item in items {
                            self.visit_item(&item);
                        }
                    }
                }
            }
        }
        verus_syn::visit::visit_item_macro(self, node);
    }
}

/// Helper struct to parse verus! macro body as a list of items
struct VerusMacroBody {
    items: Vec<Item>,
}

impl verus_syn::parse::Parse for VerusMacroBody {
    fn parse(input: verus_syn::parse::ParseStream) -> verus_syn::Result<Self> {
        let mut items = Vec::new();
        while !input.is_empty() {
            items.push(input.parse()?);
        }
        Ok(VerusMacroBody { items })
    }
}

/// Helper struct to parse cfg_if! macro body
struct CfgIfMacroBody {
    all_items: Vec<Vec<Item>>,
}

impl verus_syn::parse::Parse for CfgIfMacroBody {
    fn parse(input: verus_syn::parse::ParseStream) -> verus_syn::Result<Self> {
        use verus_syn::Token;

        let mut all_items = Vec::new();

        if input.peek(Token![if]) {
            input.parse::<Token![if]>()?;
            input.parse::<Token![#]>()?;
            let _attr_group: proc_macro2::Group = input.parse()?;

            let content;
            verus_syn::braced!(content in input);
            let mut items = Vec::new();
            while !content.is_empty() {
                items.push(content.parse()?);
            }
            all_items.push(items);
        }

        while input.peek(Token![else]) {
            input.parse::<Token![else]>()?;

            if input.peek(Token![if]) {
                input.parse::<Token![if]>()?;
                input.parse::<Token![#]>()?;
                let _attr_group: proc_macro2::Group = input.parse()?;

                let content;
                verus_syn::braced!(content in input);
                let mut items = Vec::new();
                while !content.is_empty() {
                    items.push(content.parse()?);
                }
                all_items.push(items);
            } else {
                let content;
                verus_syn::braced!(content in input);
                let mut items = Vec::new();
                while !content.is_empty() {
                    items.push(content.parse()?);
                }
                all_items.push(items);
                break;
            }
        }

        Ok(CfgIfMacroBody { all_items })
    }
}

fn parse_file(
    file_path: &Path,
    include_verus_constructs: bool,
    include_methods: bool,
    show_visibility: bool,
    show_kind: bool,
) -> Result<Vec<FunctionInfo>, String> {
    let content = fs::read_to_string(file_path)
        .map_err(|e| format!("Failed to read file {}: {}", file_path.display(), e))?;

    let syntax_tree = verus_syn::parse_file(&content)
        .map_err(|e| format!("Failed to parse file {}: {}", file_path.display(), e))?;

    let mut visitor = FunctionVisitor::new(
        Some(file_path.to_string_lossy().to_string()),
        include_verus_constructs,
        include_methods,
        show_visibility,
        show_kind,
    );
    visitor.visit_file(&syntax_tree);

    Ok(visitor.functions)
}

fn find_rust_files(path: &Path) -> Vec<PathBuf> {
    WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "rs"))
        .map(|e| e.path().to_path_buf())
        .collect()
}

fn main() {
    let args = Args::parse();

    if !args.path.exists() {
        eprintln!("Error: Path does not exist: {}", args.path.display());
        std::process::exit(1);
    }

    let mut all_functions = Vec::new();
    let mut functions_by_file: HashMap<String, Vec<FunctionInfo>> = HashMap::new();
    let mut total_files = 0;

    if args.path.is_file() {
        match parse_file(
            &args.path,
            args.include_verus_constructs,
            args.include_methods,
            args.show_visibility,
            args.show_kind,
        ) {
            Ok(functions) => {
                let file_path = args.path.to_string_lossy().to_string();
                if !functions.is_empty() {
                    functions_by_file.insert(file_path, functions.clone());
                    all_functions.extend(functions);
                    total_files = 1;
                }
            }
            Err(e) => {
                eprintln!("Error parsing file: {}", e);
                std::process::exit(1);
            }
        }
    } else {
        let rust_files = find_rust_files(&args.path);
        total_files = rust_files.len();

        for file_path in rust_files {
            match parse_file(
                &file_path,
                args.include_verus_constructs,
                args.include_methods,
                args.show_visibility,
                args.show_kind,
            ) {
                Ok(functions) => {
                    if !functions.is_empty() {
                        let path_str = file_path.to_string_lossy().to_string();
                        functions_by_file.insert(path_str, functions.clone());
                        all_functions.extend(functions);
                    }
                }
                Err(e) => {
                    eprintln!("Warning: {}", e);
                }
            }
        }
    }

    match args.format {
        OutputFormat::Json => {
            let output = ParsedOutput {
                functions: all_functions.clone(),
                functions_by_file,
                summary: Summary {
                    total_functions: all_functions.len(),
                    total_files,
                },
            };
            println!("{}", serde_json::to_string_pretty(&output).unwrap());
        }
        OutputFormat::Text => {
            // Just print function names, one per line
            let mut names: Vec<_> = all_functions.iter().map(|f| f.name.as_str()).collect();
            names.sort();
            names.dedup();
            for name in names {
                println!("{}", name);
            }
        }
        OutputFormat::Detailed => {
            for func in &all_functions {
                print!("{}", func.name);
                if let Some(ref kind) = func.kind {
                    print!(" [{}]", kind);
                }
                if let Some(ref vis) = func.visibility {
                    print!(" ({})", vis);
                }
                if let Some(ref file) = func.file {
                    print!(" @ {}:{}:{}", file, func.start_line, func.end_line);
                }
                if let Some(ref context) = func.context {
                    print!(" in {}", context);
                }
                println!();
            }
            println!("\nSummary: {} functions in {} files", all_functions.len(), total_files);
        }
    }
}

