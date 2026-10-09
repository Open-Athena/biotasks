// Pi's execution context resolves relative paths against its host cwd. Translate
// that exact directory prefix, retaining explicitly absolute sandbox paths.
export function mapRemotePath(path, localCwd, remoteCwd) {
  if (path === localCwd) return remoteCwd;
  if (path.startsWith(localCwd + "/")) {
    return remoteCwd.replace(/\/$/, "") + path.slice(localCwd.length);
  }
  return path;
}
