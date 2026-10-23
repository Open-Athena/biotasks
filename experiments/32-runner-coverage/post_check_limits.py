"""One explicit infrastructure timeout change, never a shell-command rewrite."""
def effective_timeout(args, declared, phase, test_script):
    if (args[:2] == ['docker', 'exec'] and phase == 'smoke') or (args[:2] == ['docker', 'run'] and phase == 'fresh'):
        if args[-3:] == ['bash', '-lc', test_script]:
            assert declared == 300
            return 1200
    return declared
