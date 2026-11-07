#include "music.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace pv {
namespace {
constexpr double kPi = 3.14159265358979323846;

template <typename T>
T clamp(T value, T lo, T hi) { return std::max(lo, std::min(value, hi)); }

void le16(std::ostream& f, uint16_t n) {
    f.put(static_cast<char>(n)); f.put(static_cast<char>(n >> 8));
}
void le32(std::ostream& f, uint32_t n) {
    le16(f, static_cast<uint16_t>(n)); le16(f, static_cast<uint16_t>(n >> 16));
}
void be16(std::ostream& f, uint16_t n) {
    f.put(static_cast<char>(n >> 8)); f.put(static_cast<char>(n));
}
void be32(std::ostream& f, uint32_t n) {
    be16(f, static_cast<uint16_t>(n >> 16)); be16(f, static_cast<uint16_t>(n));
}
void push_vlq(std::vector<uint8_t>& out, uint32_t n) {
    uint8_t temp[5]{}; int count = 0;
    temp[count++] = static_cast<uint8_t>(n & 127);
    while ((n >>= 7) != 0) temp[count++] = static_cast<uint8_t>(128 | (n & 127));
    for (int i = count - 1; i >= 0; --i) out.push_back(temp[i]);
}
void append_meta(std::vector<uint8_t>& out, uint8_t type,
                 const std::vector<uint8_t>& data) {
    out.push_back(0xFF); out.push_back(type);
    push_vlq(out, static_cast<uint32_t>(data.size()));
    out.insert(out.end(), data.begin(), data.end());
}
void write_track(std::ostream& f, const std::vector<uint8_t>& payload) {
    f.write("MTrk", 4);
    be32(f, static_cast<uint32_t>(payload.size()));
    f.write(reinterpret_cast<const char*>(payload.data()),
            static_cast<std::streamsize>(payload.size()));
}
struct MidiEvent {
    int tick;
    int priority; // notes off first when events share a tick
    std::vector<uint8_t> bytes;
};
void note_track(std::ostream& f, const Song& song, bool melody) {
    std::vector<uint8_t> out;
    push_vlq(out, 0);
    const std::string name = melody ? "Melodie" : "Accompagnement";
    append_meta(out, 0x03, std::vector<uint8_t>(name.begin(), name.end()));
    push_vlq(out, 0);
    const uint8_t channel = melody ? 0 : 1;
    out.push_back(static_cast<uint8_t>(0xC0 | channel)); out.push_back(0); // piano
    std::vector<MidiEvent> ev;
    for (const auto& n : song.notes) {
        if (n.melody != melody) continue;
        ev.push_back({n.start + n.duration, 0,
                     {static_cast<uint8_t>(0x80 | channel), static_cast<uint8_t>(n.pitch), 0}});
        ev.push_back({n.start, 1,
                     {static_cast<uint8_t>(0x90 | channel), static_cast<uint8_t>(n.pitch), static_cast<uint8_t>(n.velocity)}});
    }
    std::stable_sort(ev.begin(), ev.end(), [](const MidiEvent& a, const MidiEvent& b) {
        return a.tick < b.tick || (a.tick == b.tick && a.priority < b.priority);
    });
    int previous = 0;
    for (const auto& e : ev) {
        push_vlq(out, static_cast<uint32_t>(e.tick - previous));
        out.insert(out.end(), e.bytes.begin(), e.bytes.end());
        previous = e.tick;
    }
    push_vlq(out, static_cast<uint32_t>(std::max(0, song.total_ticks() - previous)));
    append_meta(out, 0x2F, {});
    write_track(f, out);
}
float shaped_note(const Note& n, uint64_t frame, unsigned sample_rate, int bpm) {
    const double frames_per_tick = 60.0 * sample_rate / (bpm * kTicksPerQuarter);
    const double start_frame = n.start * frames_per_tick;
    const double end_frame = (n.start + n.duration) * frames_per_tick;
    const double t = (static_cast<double>(frame) - start_frame) / sample_rate;
    if (t < 0.0 || static_cast<double>(frame) >= end_frame) return 0.0f;
    const double attack = clamp(t / 0.008, 0.0, 1.0);
    const double release = clamp((end_frame - frame) / (sample_rate * 0.055), 0.0, 1.0);
    const double decay = 0.88 + 0.12 * std::exp(-t * 2.0);
    const double freq = 440.0 * std::pow(2.0, (n.pitch - 69) / 12.0);
    const double phase = 2.0 * kPi * freq * t;
    const double wave = std::sin(phase) + 0.22 * std::sin(2.0 * phase) + 0.08 * std::sin(3.0 * phase);
    return static_cast<float>(0.115 * n.velocity / 127.0 * attack * release * decay * wave);
}
}

Song demo_song() {
    Song s;
    auto add = [&s](int pitch, int beat_eighth, int duration_eighth, bool melody, int velocity) {
        s.notes.push_back({pitch, beat_eighth * 240, duration_eighth * 240, velocity, melody});
    };
    // Original four-bar demonstration melody; not the historical B13 PCM signal.
    const struct { int pitch, at, length; } lead[] = {
        {72,0,2},{76,2,2},{79,4,2},{76,6,2},
        {77,8,2},{81,10,2},{79,12,4},
        {76,16,2},{79,18,1},{81,19,1},{79,20,2},{74,22,2},
        {76,24,2},{74,26,2},{72,28,4}
    };
    for (const auto& n : lead) add(n.pitch, n.at, n.length, true, 102);
    const struct { int pitch, at, length; } harmony[] = {
        {48,0,8},{60,0,8},{64,0,8},{67,0,8},
        {53,8,8},{60,8,8},{65,8,8},{69,8,8},
        {55,16,8},{59,16,8},{62,16,8},{67,16,8},
        {48,24,8},{60,24,8},{64,24,8},{67,24,8}
    };
    for (const auto& n : harmony) add(n.pitch, n.at, n.length, false, 60);
    return s;
}

void toggle_note(Song& s, int pitch, int start, int duration) {
    pitch = clamp(pitch, 0, 127);
    start = clamp(start, 0, s.total_ticks() - 1);
    duration = clamp(duration, 1, s.total_ticks() - start);
    auto it = std::find_if(s.notes.begin(), s.notes.end(), [=](const Note& n) {
        return n.melody && n.pitch == pitch && n.start == start;
    });
    if (it != s.notes.end()) s.notes.erase(it);
    else s.notes.push_back({pitch, start, duration, 98, true});
}

std::string solfege(int pitch) {
    static const char* const names[12] = {
        "Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"
    };
    return names[((pitch % 12) + 12) % 12];
}

std::vector<float> synthesize(const Song& song, unsigned sample_rate) {
    if (song.bpm < 30 || song.bpm > 300 || sample_rate < 8000 || sample_rate > 192000 ||
        song.bars < 1 || song.bars > 64 || song.beats_per_bar < 1 || song.beats_per_bar > 12)
        throw std::invalid_argument("invalid song parameters");
    for (const auto& n : song.notes)
        if (n.pitch < 0 || n.pitch > 127 || n.velocity < 1 || n.velocity > 127 ||
            n.start < 0 || n.duration < 1 || n.start + n.duration > song.total_ticks())
            throw std::invalid_argument("invalid MIDI note");
    const uint64_t count = static_cast<uint64_t>(std::llround(
        static_cast<double>(song.total_ticks()) * 60.0 * sample_rate /
        (song.bpm * kTicksPerQuarter)));
    if (count > 30'000'000) throw std::invalid_argument("song too long");
    std::vector<float> result(static_cast<size_t>(count), 0.0f);
    for (uint64_t i = 0; i < count; ++i) {
        float sample = 0.0f;
        for (const auto& n : song.notes) sample += shaped_note(n, i, sample_rate, song.bpm);
        result[static_cast<size_t>(i)] = clamp(sample, -0.95f, 0.95f);
    }
    return result;
}

bool export_wav(const std::string& filename, const std::vector<float>& mono,
                unsigned sample_rate, int repetitions, float volume, float pan) {
    if (filename.empty() || mono.empty() || sample_rate < 8000 || repetitions < 1 ||
        repetitions > 32 || !std::isfinite(volume) || !std::isfinite(pan)) return false;
    const uint64_t frames = mono.size() * static_cast<uint64_t>(repetitions);
    if (frames > (std::numeric_limits<uint32_t>::max() - 36) / 4) return false;
    std::ofstream f(filename, std::ios::binary | std::ios::trunc);
    if (!f) return false;
    const uint32_t data_bytes = static_cast<uint32_t>(frames * 4);
    f.write("RIFF", 4); le32(f, 36 + data_bytes); f.write("WAVE", 4);
    f.write("fmt ", 4); le32(f, 16); le16(f, 1); le16(f, 2);
    le32(f, sample_rate); le32(f, sample_rate * 4); le16(f, 4); le16(f, 16);
    f.write("data", 4); le32(f, data_bytes);
    const float angle = (clamp(pan, -1.0f, 1.0f) + 1.0f) * static_cast<float>(kPi / 4.0);
    const float lv = clamp(volume, 0.0f, 1.0f) * std::cos(angle);
    const float rv = clamp(volume, 0.0f, 1.0f) * std::sin(angle);
    for (uint64_t i = 0; i < frames; ++i) {
        const float m = mono[static_cast<size_t>(i % mono.size())];
        const auto q = [](float v) -> int16_t {
            return static_cast<int16_t>(std::lrint(clamp(v, -1.0f, 1.0f) * 32767.0f));
        };
        le16(f, static_cast<uint16_t>(q(m * lv)));
        le16(f, static_cast<uint16_t>(q(m * rv)));
    }
    return f.good();
}

bool export_midi(const std::string& filename, const Song& song) {
    if (filename.empty() || song.bpm < 30 || song.bpm > 300 || song.beats_per_bar != 4 ||
        song.bars < 1 || song.bars > 64) return false;
    for (const auto& n : song.notes)
        if (n.pitch < 0 || n.pitch > 127 || n.start < 0 || n.duration < 1 ||
            n.start + n.duration > song.total_ticks() || n.velocity < 1 || n.velocity > 127)
            return false;
    std::ofstream f(filename, std::ios::binary | std::ios::trunc);
    if (!f) return false;
    f.write("MThd", 4); be32(f, 6); be16(f, 1); be16(f, 3); be16(f, kTicksPerQuarter);
    std::vector<uint8_t> meta;
    push_vlq(meta, 0);
    const std::string name = "Petite Victoire";
    append_meta(meta, 0x03, std::vector<uint8_t>(name.begin(), name.end()));
    push_vlq(meta, 0);
    const uint32_t us_per_beat = 60'000'000u / static_cast<uint32_t>(song.bpm);
    append_meta(meta, 0x51, {static_cast<uint8_t>(us_per_beat >> 16),
                              static_cast<uint8_t>(us_per_beat >> 8),
                              static_cast<uint8_t>(us_per_beat)});
    push_vlq(meta, 0); append_meta(meta, 0x58, {4,2,24,8});
    push_vlq(meta, 0); append_meta(meta, 0x59, {0,0}); // C major
    push_vlq(meta, static_cast<uint32_t>(song.total_ticks()));
    append_meta(meta, 0x2F, {});
    write_track(f, meta);
    note_track(f, song, true);
    note_track(f, song, false);
    return f.good();
}

void Playback::set_pcm(const std::vector<float>& mono) noexcept {
    active_.store(false);
    pcm_ = &mono;
    position_.store(0);
}
void Playback::set_volume(float v) noexcept {
    volume_.store(std::isfinite(v) ? clamp(v, 0.0f, 1.0f) : 0.0f);
}
void Playback::set_pan(float v) noexcept {
    pan_.store(std::isfinite(v) ? clamp(v, -1.0f, 1.0f) : 0.0f);
}
void Playback::render(float* out, size_t frames) noexcept {
    if (!out) return;
    const auto& pcm = *pcm_;
    auto pos = position_.load();
    bool running = active_.load();
    if (!running) {
        std::fill(out, out + frames*2, 0.0f);
        smooth_left_ = 0.0f;
        smooth_right_ = 0.0f;
        return;
    }
    const bool loop = loop_.load();
    const float vol = volume_.load();
    const float angle = (pan_.load() + 1.0f) * static_cast<float>(kPi / 4.0);
    const float l = vol * std::cos(angle);
    const float r = vol * std::sin(angle);
    for (size_t i = 0; i < frames; ++i) {
        float value = 0.0f;
        if (running && !pcm.empty()) {
            if (pos >= pcm.size()) {
                if (loop) pos = 0;
                else running = false;
            }
            if (running) value = pcm[static_cast<size_t>(pos++)];
        }
        smooth_left_ += 0.02f * (l - smooth_left_);
        smooth_right_ += 0.02f * (r - smooth_right_);
        out[i * 2] = value * smooth_left_;
        out[i * 2 + 1] = value * smooth_right_;
    }
    position_.store(pos);
    if (!running) active_.store(false);
}

} // namespace pv
