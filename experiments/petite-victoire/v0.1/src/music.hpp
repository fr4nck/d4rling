#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace pv {

constexpr int kTicksPerQuarter = 480;
constexpr unsigned kSampleRate = 44100;

struct Note {
    int pitch = 60;         // MIDI 0..127
    int start = 0;          // ticks from start of piece
    int duration = 480;     // ticks
    int velocity = 90;      // MIDI 1..127
    bool melody = true;
};

struct Song {
    int bpm = 120;
    int beats_per_bar = 4;
    int bars = 4;
    std::vector<Note> notes;
    int total_ticks() const { return bars * beats_per_bar * kTicksPerQuarter; }
};

Song demo_song();
void toggle_note(Song& song, int pitch, int start, int duration = kTicksPerQuarter);
std::string solfege(int pitch);

// Mono, deliberately pre-rendered outside the real-time audio callback.
std::vector<float> synthesize(const Song& song, unsigned sample_rate = kSampleRate);

// No implicit filesystem writes: only explicit output filenames.
bool export_wav(const std::string& filename, const std::vector<float>& mono,
                unsigned sample_rate = kSampleRate, int repetitions = 1,
                float volume = 0.7f, float pan = 0.0f);
bool export_midi(const std::string& filename, const Song& song);

struct Playback {
    explicit Playback(const std::vector<float>& mono) : pcm_(&mono) {}
    void play() noexcept { position_.store(0); active_.store(true); }
    void stop() noexcept { active_.store(false); }
    void set_loop(bool yes) noexcept { loop_.store(yes); }
    void set_volume(float value) noexcept;
    void set_pan(float value) noexcept;
    bool playing() const noexcept { return active_.load(); }
    bool looping() const noexcept { return loop_.load(); }
    uint64_t position() const noexcept { return position_.load(); }
    float volume() const noexcept { return volume_.load(); }
    float pan() const noexcept { return pan_.load(); }
    // Only call set_pcm when the audio device is stopped.
    void set_pcm(const std::vector<float>& mono) noexcept;
    // Float32LE stereo, interleaved. No allocations, syscalls or blocking I/O.
    void render(float* out, size_t frames) noexcept;

private:
    const std::vector<float>* pcm_;
    std::atomic<uint64_t> position_{0};
    std::atomic<bool> active_{false};
    std::atomic<bool> loop_{true};
    std::atomic<float> volume_{0.7f};
    std::atomic<float> pan_{0.0f};
    // Render-thread-only gain state for click-free fader/pan moves.
    float smooth_left_ = 0.0f;
    float smooth_right_ = 0.0f;
};

} // namespace pv
