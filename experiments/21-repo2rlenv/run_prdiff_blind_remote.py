"""Explicit blind mode; requires matching native runtime acceptance evidence."""
from run_prdiff_provider_remote import main

if __name__=='__main__':
    raise SystemExit(main(mode='blind'))
