# Terraform modules

Empty for now. The Phase 1 scaffold keeps everything in the root module
(`terraform/main.tf`) since it's small enough to read in one file. Split
resources into modules here only if/when the root module actually grows
unwieldy — don't add module indirection preemptively.
