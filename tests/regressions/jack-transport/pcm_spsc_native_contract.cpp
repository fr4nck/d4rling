#include <algorithm>
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

class PCMQueue {
    const std::size_t cap_;
    const unsigned channels_;
    const unsigned rate_;
    std::vector<float> data_;
    std::atomic<std::uint64_t> rd_{0}, wr_{0};
    std::atomic<std::uint64_t> clock_{0}, over_{0}, under_{0};
    std::atomic<bool> active_{false};
public:
    PCMQueue(unsigned channels, std::size_t capacity, unsigned rate)
        : cap_(capacity), channels_(channels), rate_(rate),
          data_(channels * capacity, 0.0f) {
        if ((channels != 1 && channels != 2) || !capacity || !rate)
            throw std::invalid_argument("invalid PCM dimensions");
    }
    // Call start/stop only when producer and consumer are quiescent.
    bool start() noexcept { return !active_.exchange(true); }
    bool stop() noexcept {
        if (!active_.exchange(false)) return false;
        rd_.store(wr_.load(std::memory_order_relaxed), std::memory_order_relaxed);
        return true;
    }
    // Single producer, planar float32, preallocated channel pointers.
    bool write(const float* const* in, std::size_t n) noexcept {
        if (!active_.load(std::memory_order_acquire)) return false;
        const auto w = wr_.load(std::memory_order_relaxed);
        const auto r = rd_.load(std::memory_order_acquire);
        if (n > cap_ || n > cap_ - static_cast<std::size_t>(w - r)) {
            over_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        for (std::size_t i = 0; i < n; ++i)
            for (unsigned c = 0; c < channels_; ++c)
                data_[c * cap_ + (w + i) % cap_] = in[c][i];
        wr_.store(w + n, std::memory_order_release);
        return true;
    }
    // Single consumer. Caller owns output buffers; zero-fill underrun.
    std::size_t read(float* const* out, std::size_t n) noexcept {
        if (!active_.load(std::memory_order_acquire)) {
            for (unsigned c = 0; c < channels_; ++c)
                std::fill_n(out[c], n, 0.0f);
            return 0;
        }
        const auto r = rd_.load(std::memory_order_relaxed);
        const auto w = wr_.load(std::memory_order_acquire);
        const auto count = std::min(n, static_cast<std::size_t>(w - r));
        for (unsigned c = 0; c < channels_; ++c) {
            for (std::size_t i = 0; i < count; ++i)
                out[c][i] = data_[c * cap_ + (r + i) % cap_];
            std::fill(out[c] + count, out[c] + n, 0.0f);
        }
        rd_.store(r + count, std::memory_order_release);
        clock_.fetch_add(n, std::memory_order_relaxed);
        under_.fetch_add(n - count, std::memory_order_relaxed);
        return count;
    }
    std::uint64_t clock() const noexcept { return clock_.load(); }
    std::uint64_t overruns() const noexcept { return over_.load(); }
    std::uint64_t underrun_frames() const noexcept { return under_.load(); }
    unsigned rate() const noexcept { return rate_; }
};

#define TEST(name, condition) do { \
    ++count; if (!(condition)) { std::cout << "FAIL: " << name << '\n'; return 1; } \
    std::cout << "PASS: " << name << '\n'; \
} while (0)

int main() {
    unsigned count = 0;
    std::array<float, 1024> l{}, r{}, a{}, b{};
    for (std::size_t i = 0; i < l.size(); ++i) {
        l[i] = static_cast<float>(i + 1);
        r[i] = static_cast<float>(i + 1001);
    }
    const float* in[] = {l.data(), r.data()};
    float* out[] = {a.data(), b.data()};

    {
        bool ok = true;
        for (auto n : {0u, 1u, 64u, 128u, 1024u}) {
            PCMQueue q(2, 1024, 48000);
            q.start();
            ok &= q.write(in, n) && q.read(out, n) == n;
            for (std::size_t i = 0; i < n; ++i)
                ok &= (a[i] == l[i] && b[i] == r[i]);
        }
        TEST("frame sizes", ok);
    }
    {
        PCMQueue q(1, 4, 44100);
        const float* one[] = {l.data()}; float* dest[] = {a.data()};
        q.start();
        TEST("mono", q.write(one, 2) && q.read(dest, 2) == 2 && a[1] == l[1]);
    }
    {
        PCMQueue q(2, 4, 48000); q.start();
        bool ok = q.write(in, 3) && q.read(out, 2) == 2;
        const float* tail[] = {l.data()+3, r.data()+3};
        ok &= q.write(tail, 2) && q.read(out, 3) == 3;
        ok &= a[0] == l[2] && a[1] == l[3] && a[2] == l[4];
        ok &= b[0] == r[2] && b[1] == r[3] && b[2] == r[4];
        TEST("wraparound", ok);
    }
    {
        PCMQueue q(2, 3, 48000); q.start();
        bool ok = q.write(in, 2) && !q.write(in, 2);
        ok &= q.overruns() == 1 && q.read(out, 2) == 2;
        ok &= a[0] == l[0] && a[1] == l[1];
        TEST("overflow atomicity", ok);
    }
    {
        PCMQueue q(2, 4, 48000); q.start();
        bool ok = q.write(in, 1) && q.read(out, 4) == 1;
        ok &= a[0] == l[0] && b[0] == r[0];
        for (int i = 1; i < 4; ++i) ok &= a[i] == 0 && b[i] == 0;
        TEST("underrun zero fill", ok && q.underrun_frames() == 3);
    }
    {
        PCMQueue q(2, 4, 48000); q.start();
        bool ok = q.write(in, 1) && q.stop() && q.start();
        ok &= q.read(out, 1) == 0 && a[0] == 0 && b[0] == 0;
        TEST("stop and restart", ok);
    }
    {
        bool ok = true;
        for (auto hz : {44100u, 48000u, 96000u}) {
            PCMQueue q(2, 256, hz); q.start();
            q.read(out, 64); q.read(out, 128);
            ok &= q.clock() == 192 && q.rate() == hz;
        }
        TEST("rates and monotonic frame clock", ok);
    }
    {
        PCMQueue q(2, 4, 48000);
        TEST("stopped write refused", !q.write(in, 1));
        TEST("invalid double stop", !q.stop());
    }
    {
        bool ok = false;
        try { PCMQueue bad(3, 4, 48000); } catch (const std::invalid_argument&) { ok = true; }
        TEST("invalid configuration", ok);
    }
    {
        PCMQueue q(2, 256, 48000); q.start();
        std::atomic<bool> good{true};
        constexpr unsigned N = 50000;
        std::thread producer([&] {
            for (unsigned i = 1; i <= N; ++i) {
                const float x = static_cast<float>(i);
                const float* pair[] = {&x, &x};
                while (!q.write(pair, 1)) std::this_thread::yield();
            }
        });
        std::thread consumer([&] {
            unsigned last = 0;
            while (last < N) {
                float x = 0, y = 0; float* pair[] = {&x, &y};
                if (!q.read(pair, 1)) { std::this_thread::yield(); continue; }
                if (x != float(last + 1) || y != x) good = false;
                ++last;
            }
        });
        producer.join(); consumer.join();
        TEST("SPSC 50000 frames in order", good.load());
    }
    std::cout << "JACK01E2_PASS=" << count << "/" << count << "\n";
    std::cout << "JACK01E2_STATUS=PASS_NATIVE_MODEL_ONLY\n";
    std::cout << "REAL_JACK_TEST=NOT_EXECUTED\n";
    return 0;
}
