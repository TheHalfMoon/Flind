use std::env;
use std::fs;
use std::path::PathBuf;

const API_CLI_BUNDLE: &str = "lib/posthog-api-cli.mjs";

fn write_api_cli_bundle_include() {
    let manifest_dir =
        PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR is set by cargo"));
    let bundle_path = manifest_dir.join(API_CLI_BUNDLE);
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR is set by cargo"));
    let out_path = out_dir.join("api_cli_bundle.rs");

    println!("cargo:rerun-if-changed={}", bundle_path.display());

    let contents = if bundle_path.is_file() {
        let bundle_path_literal = format!("{bundle_path:?}");
        format!("const EMBEDDED_API_CLI_BUNDLE: Option<&[u8]> = Some(include_bytes!({bundle_path_literal}));\n")
    } else {
        "const EMBEDDED_API_CLI_BUNDLE: Option<&[u8]> = None;\n".to_string()
    };

    fs::write(out_path, contents).expect("write embedded API CLI bundle include");
}

pub fn main() {
    write_api_cli_bundle_include();
}
