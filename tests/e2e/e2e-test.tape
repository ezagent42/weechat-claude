# VHS tape for recording E2E test execution
# Usage: cd project-root && vhs tests/e2e/e2e-test.tape

Output "./e2e-test.mp4"

Require bash
Require weechat
Require claude
Require tmux
Require zenohd

Set Shell "bash"
Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Width 1200
Set Height 700
Set Padding 10
Set TypingSpeed 20ms
Set PlaybackSpeed 5

Type "bash tests/e2e/e2e-test.sh"
Enter

# E2E tests take ~3 minutes
Sleep 240s
