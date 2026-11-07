#include "music.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    std::string wav, midi;
    int loops = 1;
    int tempo = 120;
    bool print = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if ((arg == "--wav" || arg == "--midi" || arg == "--tempo" || arg == "--loops") && i+1 < argc) {
            const std::string value = argv[++i];
            if (arg == "--wav") wav = value;
            if (arg == "--midi") midi = value;
            if (arg == "--tempo") tempo = std::atoi(value.c_str());
            if (arg == "--loops") loops = std::atoi(value.c_str());
        } else if (arg == "--notes") print = true;
        else {
            std::cerr << "Usage: petite-victoire [--notes] [--wav PATH] [--midi PATH] "
                         "[--tempo 30..300] [--loops 1..32]\n";
            return 2;
        }
    }
    if (tempo < 30 || tempo > 300 || loops < 1 || loops > 32) {
        std::cerr << "Invalid tempo or loop count\n";
        return 2;
    }
    if (wav.empty() && midi.empty() && !print) {
        std::cout << "No output written; specify --wav / --midi / --notes\n";
        return 0;
    }
    if ((!wav.empty() && std::filesystem::exists(wav)) ||
        (!midi.empty() && std::filesystem::exists(midi)) ||
        (!wav.empty() && wav == midi)) {
        std::cerr << "Refusing to overwrite an existing output or use the same filename\n";
        return 3;
    }
    try {
        auto song = pv::demo_song();
        song.bpm = tempo;
        if (print) {
            std::cout << "Petite Victoire (original draft) : " << tempo << " BPM, "
                      << song.bars << " bars, " << song.notes.size() << " notes\n";
            for (const auto& n : song.notes)
                if (n.melody)
                    std::cout << "tick=" << n.start << "  " << pv::solfege(n.pitch)
                              << " MIDI=" << n.pitch << "  duree=" << n.duration << "\n";
        }
        if (!midi.empty()) {
            if (!pv::export_midi(midi, song)) return 4;
            std::cout << "MIDI=" << midi << "\n";
        }
        if (!wav.empty()) {
            auto samples = pv::synthesize(song);
            if (!pv::export_wav(wav, samples, pv::kSampleRate, loops)) return 5;
            std::cout << "WAV=" << wav << "\n";
            std::cout << "FRAMES=" << samples.size() * static_cast<size_t>(loops) << "\n";
        }
    } catch (const std::exception& exc) {
        std::cerr << "ERROR=" << exc.what() << "\n";
        return 6;
    }
    return 0;
}
