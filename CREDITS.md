# Credits and provenance

This fork builds on other people's work. Original copyright and license notices
remain in their files; this document supplements them.

## Darling and its dependencies

- [darlinghq/darling](https://github.com/darlinghq/darling), created by Lubos Dolezel
  and developed by the Darling contributors. The original Git history is retained,
  including author and committer metadata. See [CONTRIBUTORS.md](CONTRIBUTORS.md)
  and the [upstream contributor history](https://github.com/darlinghq/darling/graphs/contributors).
- Latest upstream baseline incorporated on 2026-10-15:
  `60ba801decee7a00782f74f6be4c8ffb013f79ff`.
  This already includes, among many others, jlucfarias' HIToolbox build fix
  [upstream PR 1779](https://github.com/darlinghq/darling/pull/1779).
- Darling's main license is [GPL-3.0](LICENSE). Imported components and submodules
  keep their own authors, notices and licenses, including Apple open-source
  components and Cocotron. The main license does not replace those component
  licenses.
- Submodule repositories remain with their original owners and at the revisions
  recorded by Git. Their URLs are absolute so a clone of this personal fork does
  not require creating sibling repositories under fr4nck.

## HIToolbox window error reporting (lot 1)

- Input: `darling-hitoolbox-lot1.zip`, supplied by fr4nck from the earlier
  ChatGPT-assisted work. No separate human author is established by that archive.
- Archive SHA-256:
  `1db07936186425e66ec0fbcde4361e1aecabdc5aaa54391b04c9660bdf408708`.
- Baseline source: Darling's `MacWindows.cpp` at the baseline above, Git blob
  `b328f28495f70dbd6f80120343c6124b87e9a46f`.
- Import commit: `2b4a018fc2a71d12844aa0438075422756816685`.
- The supplied source correction and 25 test assertions were imported; the
  runners and integration documentation were adapted with OpenAI Codex.
  These additions follow the repository's GPL license.

## CoreAudio / CarbonCore C API declaration fixes

- Original author: **Cristian Magherusan-Stanciu** (`cristim`).
- Source: [VibeDarling/darling PR 18](https://github.com/VibeDarling/darling/pull/18).
- Original commit:
  [df1fe1b560b25310f83e64f3d1fa5a9be7f0a9a2](https://github.com/VibeDarling/darling/commit/df1fe1b560b25310f83e64f3d1fa5a9be7f0a9a2).
- The original commit records assistance from Claude Opus 5 (1M context).
- Port commit: `1cf634b46d1c6eed55547862e4ed3739edc91559`, prepared with OpenAI
  Codex. Its message includes the original author's co-author attribution,
  source commit and PR, original AI-assistance record, and port-assistance record.
- Scope: the five-file declaration/definition correction only. Existing copyright
  and GPL notices are retained.

## Recording future imports

For every future reused change, record its project URL, author(s), source commit
or archive hash, applicable license, local integration commit and adaptations.
Preserve existing notices and author metadata. Record any disclosed AI assistance
as provenance; do not attribute AI-assisted work to an invented human author.
Use merges to retain upstream history. For ports, record source references and
author attribution in the commit as well as this file.

Genki ALSA/CoreMIDI, the other examined VibeDarling MIDI and Cocotron patches,
and the Carbon event-loop WIP have not been imported into this fork.

## Carbon callback and window-target contracts

Prepared for fr4nck with OpenAI Codex, based on personal integration commit
b932d448bbb317654a45640717925823d2fd3fb0. The original
[Apple Carbon Event Manager Reference, archived mirror](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html)
was consulted for EventHandlerProcPtr, EventHandlerUPP and GetWindowEventTarget.
No external implementation was copied. Existing Darling notices and history are
retained; new regression sources use GPL-3.0-or-later. The follow-up commit records
these changes together with the tests and validation note.

## Carbon event metadata and lifetime

Prepared for fr4nck with OpenAI Codex on top of
c003abfdad4adebc327d8c5c1875d9761ef5b4d2. Existing Darling authors and the source
GPL notice are retained. New regression files use GPL-3.0-or-later.
The Apple Carbon Event Manager Reference linked above was consulted for event
creation and ownership contracts; the pinned
[Darling Libc time.h](https://github.com/darlinghq/darling-Libc/blob/5a38c8dabf9e76b39407c24bc13134e33e5594e6/include/time.h)
was checked for clock declarations. No external implementation was copied.
Host tests use an explicitly identified test-only CF allocator adapter;
they do not validate the actual CoreFoundation runtime.
