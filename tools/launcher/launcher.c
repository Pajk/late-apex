/*
 * Native launcher for Late Apex.app.
 *
 * A .app whose CFBundleExecutable is a shell script has no Mach-O header, so
 * Finder cannot read an architecture from it and falls back to labelling the
 * bundle "Intel". This is a real binary, built for arm64 and x86_64, so the
 * bundle reports as Universal and starts natively on Apple Silicon.
 *
 * All it does is locate the game directory and hand over to the virtualenv's
 * Python via execv - the game process itself is whatever architecture that
 * interpreter is (arm64 on Apple Silicon).
 */

#include <errno.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <sys/wait.h>
#include <limits.h>

#ifndef FALLBACK_ROOT
#define FALLBACK_ROOT ""
#endif

static int is_game_root(const char *root)
{
    char probe[PATH_MAX];
    struct stat st;
    if (root == NULL || root[0] == '\0')
        return 0;
    snprintf(probe, sizeof(probe), "%s/main.py", root);
    return stat(probe, &st) == 0;
}

/* Strip `levels` trailing path components, in place. */
static void climb(char *path, int levels)
{
    for (int i = 0; i < levels; i++) {
        char *slash = strrchr(path, '/');
        if (slash == NULL)
            return;
        *slash = '\0';
    }
}

static void alert(const char *message)
{
    char script[1024];
    snprintf(script, sizeof(script),
             "display dialog \"%s\" buttons {\"OK\"} "
             "with title \"Late Apex\" with icon caution",
             message);
    char *argv[] = {"/usr/bin/osascript", "-e", script, NULL};
    pid_t pid = fork();
    if (pid == 0) {
        execv(argv[0], argv);
        _exit(1);
    } else if (pid > 0) {
        int status;
        waitpid(pid, &status, 0);
    }
}

int main(int argc, char *argv[])
{
    char exec_path[PATH_MAX];
    uint32_t size = sizeof(exec_path);
    char root[PATH_MAX];

    if (_NSGetExecutablePath(exec_path, &size) != 0) {
        alert("Could not determine the application path.");
        return 1;
    }

    /* .../<root>/Late Apex.app/Contents/MacOS/LateApex */
    char resolved[PATH_MAX];
    if (realpath(exec_path, resolved) == NULL)
        strncpy(resolved, exec_path, sizeof(resolved) - 1);
    strncpy(root, resolved, sizeof(root) - 1);
    root[sizeof(root) - 1] = '\0';
    climb(root, 4);

    if (!is_game_root(root)) {
        /* The bundle was moved away from the sources: fall back to the path
         * recorded when it was built. */
        strncpy(root, FALLBACK_ROOT, sizeof(root) - 1);
        root[sizeof(root) - 1] = '\0';
    }

    if (!is_game_root(root)) {
        alert("Late Apex cannot find its game files.\\n\\n"
              "Keep this app next to the late-apex folder, or run "
              "./run.sh from that folder instead.");
        return 1;
    }

    if (chdir(root) != 0) {
        alert("Could not open the game folder.");
        return 1;
    }

    char python[PATH_MAX];
    snprintf(python, sizeof(python), "%s/.venv/bin/python", root);
    if (access(python, X_OK) != 0) {
        alert("Late Apex needs its Python environment.\\n\\n"
              "Open Terminal in the game folder and run:\\n"
              "    ./run.sh\\n\\n"
              "After that this app will launch directly.");
        return 1;
    }

    /* python main.py [args...] */
    char **args = calloc(argc + 3, sizeof(char *));
    if (args == NULL)
        return 1;
    args[0] = python;
    args[1] = "main.py";
    for (int i = 1; i < argc; i++)
        args[i + 1] = argv[i];
    args[argc + 1] = NULL;

    execv(python, args);
    alert("Failed to start the game interpreter.");
    return 1;
}
