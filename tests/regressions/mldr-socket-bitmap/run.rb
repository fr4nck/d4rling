# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from VibeDarling/darling tests/mldr-socket-bitmap-shrink.rb.
# Extract production source helpers and compile the shared deterministic host probe.
# Usage: ruby tests/regressions/mldr-socket-bitmap/run.rb [REPO_ROOT]
require 'tmpdir'
require 'open3'

root = ARGV.fetch(0, File.expand_path('../../..', __dir__))
loader = File.read(File.join(root, 'src/startup/mldr/mldr.c'))
types = loader[/typedef struct socket_bitmap \{.*?(?=static int socket_bitmap_get)/m] or abort 'bitmap types missing'
funcs = loader[/static int socket_bitmap_get.*?^static void socket_bitmap_put.*?^\};\n/m] or abort 'bitmap helpers missing'
template = File.read(File.join(__dir__, 'probe.c.in'))
['@@BITMAP_TYPES@@', '@@BITMAP_FUNCS@@'].each do |mark|
  abort "template marker #{mark} count incorrect" unless template.scan(mark).length == 1
end
harness = template.sub('@@BITMAP_TYPES@@', types).sub('@@BITMAP_FUNCS@@', funcs)
compiler = ENV.fetch('CLANG', 'clang')
Dir.mktmpdir('bitmap-shrink-') do |dir|
  src = File.join(dir, 'probe.c')
  exe = File.join(dir, 'probe')
  File.write(src, harness)
  cmd = [compiler, '-pthread', '-g', '-O1', '-std=gnu11', '-Wall', '-Wextra',
         '-fno-omit-frame-pointer', '-fsanitize=address,undefined',
         '-fno-sanitize-recover=all', src, '-o', exe]
  out, status = Open3.capture2e(*cmd)
  abort "COMPILE=FAIL\n#{out}" unless status.success?
  puts 'COMPILE=PASS'
  puts out unless out.empty?
  env = { 'ASAN_OPTIONS' => 'detect_leaks=1:halt_on_error=1:abort_on_error=1',
          'UBSAN_OPTIONS' => 'halt_on_error=1:print_stacktrace=1' }
  out, status = Open3.capture2e(env, exe, rlimit_core: 0)
  puts out
  abort 'FAIL: deterministic bitmap invariants or sanitizers' unless status.success? &&
    out.include?('PASS: deterministic mldr bitmap regression')
  puts 'MLDR_PR6_DETERMINISTIC=PASS'
end
