def cached(main_fn, on=None, minutes_to_expire=10):
    import builtins
    import os
    import sys
    from io import StringIO
    from joblib import Memory
    from datetime import datetime, timedelta
    from filelock import FileLock

    # check if we should actually run
    on = on or []
    checks = on
#    print(f"on :{on}, {type(on)}, {sys.argv}")
    if not isinstance(on, (list, tuple)):
        checks = [on]
    if not any(chk(sys.argv) for chk in checks):
        # input(f"on :{on}, {type(on)}, {sys.argv}\nPress Enter to continue...")
        sys.exit(main_fn())

    # ok, we should cache this
    toolname = os.path.basename(sys.argv[0])
    lockfile = f"D:/tmp/rf_{toolname}.lock"
    cachefile = f'D:/tmp/rf_{toolname}.cache'
    delayed_rc = 0
    memory = Memory(cachefile, verbose=0)
    cache_expire = timedelta(minutes=minutes_to_expire)

    @memory.cache
    def latest():
        # just a helper so we can check cache expiration
        return datetime.now()

    def exit(rc):
        # intercept calling of the exit builtin
        global delayed_exit
        delayed_rc = rc

    builtins.exit = exit

    @memory.cache
    def cached_run(*args, **kwargs):
        # cache stdout, stderr
        cached_out = StringIO()
        _stderr, _stdout = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = cached_out, cached_out
            main_fn()
        except:
            sys.stdout, sys.stderr = _stderr, _stdout
            raise
        finally:
            sys.stdout, sys.stderr = _stderr, _stdout
        return delayed_rc, cached_out.getvalue()

    # should we clear the cache since last call?
    cache_expired = latest() + cache_expire < datetime.now()
    cache_ignore = 'RUNFAST_NOCACHE' in os.environ
    if cache_expired or cache_ignore:
        memory.clear(warn=cache_ignore)
        latest()
    # make sure no concurrent calls running for this same tool
    lock = FileLock(lockfile)
    with lock:
        rc, output = cached_run(sys.argv)
        sys.stdout.write(output)
        sys.stdout.flush()
        sys.exit(delayed_rc)
