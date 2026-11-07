#include "music.hpp"
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <string>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void check(bool pass, const char* msg) {
    if (!pass) throw std::runtime_error(msg);
}
}

int main() {
    try {
        const pv::Song s = pv::demo_song();
        check(s.bpm == 120 && s.total_ticks() == 7680, "song timing");
        check(s.notes.size() == 31, "note count");
        check(std::count_if(s.notes.begin(), s.notes.end(), [](const pv::Note& n){return n.melody;}) == 15,
              "melody count");
        check(pv::solfege(60) == "Do" && pv::solfege(69) == "La", "solfege");
        check(pv::solfege(66) == "Fa#", "accidental");

        pv::Song modified = s;
        pv::toggle_note(modified, 72, 0);
        check(modified.notes.size() == 30, "toggle removal");
        pv::toggle_note(modified, 72, 0);
        check(modified.notes.size() == 31, "toggle insertion");

        const std::vector<float> pcm = pv::synthesize(s, 44100);
        check(pcm.size() == 352800, "duration 8 seconds at 44100");
        check(std::abs(pcm.front()) < 0.00001, "zero crossing at start");
        check(std::abs(pcm.back()) < 0.001, "fade at end");
        const auto peak = std::max_element(pcm.begin(), pcm.end(), [](float a,float b){return std::abs(a) < std::abs(b);});
        check(peak != pcm.end() && std::abs(*peak) > 0.01f && std::abs(*peak) <= 0.95f, "peak amplitude");
        bool threw = false;
        try { pv::Song invalid = s; invalid.notes[0].pitch = 130; (void)pv::synthesize(invalid); }
        catch (const std::invalid_argument&) { threw = true; }
        check(threw, "reject invalid pitch");

        pv::Playback player(pcm);
        std::vector<float> frame(2048, -1.0f);
        player.render(frame.data(), 1024);
        check(std::all_of(frame.begin(), frame.end(), [](float x){return x == 0.0f;}), "silence before play");
        player.play();
        player.set_pan(-1.0f);
        player.set_volume(1.0f);
        player.render(frame.data(), 1024);
        check(player.position() == 1024, "playback progression");
        float max_left = 0, max_right = 0;
        for (size_t i=0; i<1024; ++i) {
            max_left = std::max(max_left, std::abs(frame[i*2]));
            max_right = std::max(max_right, std::abs(frame[i*2+1]));
        }
        check(max_left > 0.005f && max_right < 1e-5f, "hard left pan");
        player.set_pan(1.0f);
        player.render(frame.data(), 1024);
        max_left = 0; max_right = 0;
        for (size_t i=0; i<1024; ++i) {
            max_left = std::max(max_left, std::abs(frame[i*2]));
            max_right = std::max(max_right, std::abs(frame[i*2+1]));
        }
        check(max_right > 0.005f && std::abs(frame[2*1023]) < 1e-4f, "hard right pan ramp");
        player.set_loop(false);
        player.play();
        std::vector<float> all((pcm.size()+128)*2);
        player.render(all.data(), pcm.size()+128);
        check(!player.playing(), "stops after song when loop disabled");
        check(all.back() == 0.0f, "trailing silence");
        player.set_loop(true);
        player.play();
        player.render(all.data(), pcm.size()+128);
        check(player.playing() && player.position() == 128, "wraps on loop");

        const std::string path = "pv-test-output.wav";
        check(pv::export_wav(path, pcm), "WAV export");
        const std::string mid = "pv-test-output.mid";
        check(pv::export_midi(mid, s), "MIDI export");
        auto read_file = [](const std::string& p) {
            std::ifstream f(p, std::ios::binary);
            return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)),
                                        std::istreambuf_iterator<char>());
        };
        const auto w = read_file(path);
        check(w.size() == 44 + pcm.size()*4, "WAV size");
        check(std::string(w.begin(), w.begin()+4) == "RIFF" &&
              std::string(w.begin()+8,w.begin()+12) == "WAVE", "WAV magic");
        check(w[22] == 2 && w[23] == 0 && w[34] == 16 && w[35] == 0,
              "WAV S16 stereo");
        check(w[24] == 0x44 && w[25] == 0xAC && w[26] == 0 && w[27] == 0,
              "WAV 44100 Hz");
        const auto m = read_file(mid);
        check(m.size() > 150, "MIDI nonempty");
        check(std::string(m.begin(), m.begin()+4) == "MThd", "MIDI magic");
        check(m[8] == 0 && m[9] == 1 && m[10] == 0 && m[11] == 3,
              "MIDI type 1, three tracks");
        check(m[12] == 1 && m[13] == 224, "MIDI 480 ticks per beat");
        int trackcount=0, note_on=0, note_off=0;
        size_t cursor=14;
        auto read_var = [&](size_t& pos, size_t end) -> unsigned {
            unsigned v=0;
            for(int i=0;i<4;i++) {
                check(pos < end,"MIDI short varlen");
                const uint8_t byte=m[pos++];
                v=(v<<7)|(byte&127);
                if ((byte&128)==0) return v;
            }
            throw std::runtime_error("MIDI excessive varlen");
        };
        while (cursor<m.size()) {
            check(cursor+8<=m.size() &&
                  std::string(m.begin()+cursor,m.begin()+cursor+4)=="MTrk",
                  "MIDI track header");
            ++trackcount;
            const size_t length=(static_cast<size_t>(m[cursor+4])<<24) |
                (static_cast<size_t>(m[cursor+5])<<16) |
                (static_cast<size_t>(m[cursor+6])<<8) | m[cursor+7];
            cursor+=8;
            const size_t end=cursor+length;
            check(end<=m.size(),"MIDI truncated track");
            int tick=0, end_events=0;
            while(cursor<end) {
                tick+=static_cast<int>(read_var(cursor,end));
                check(cursor<end,"MIDI truncated event");
                const unsigned status=m[cursor++];
                if(status==0xff) {
                    check(cursor<end,"MIDI missing meta type");
                    const uint8_t type=m[cursor++];
                    const size_t bytes=read_var(cursor,end);
                    check(cursor+bytes<=end,"MIDI truncated meta");
                    if(type==0x2f) ++end_events;
                    cursor+=bytes;
                } else if ((status&0xf0)==0xc0 || (status&0xf0)==0xd0) {
                    check(cursor+1<=end,"MIDI program change");
                    cursor+=1;
                } else if(status>=0x80 && status<=0xef) {
                    check(cursor+2<=end,"MIDI truncated channel event");
                    if((status&0xf0)==0x90 && m[cursor+1]!=0) ++note_on;
                    if((status&0xf0)==0x80 || ((status&0xf0)==0x90 && m[cursor+1]==0)) ++note_off;
                    cursor+=2;
                } else {
                    throw std::runtime_error("MIDI unexpected status");
                }
            }
            check(tick==s.total_ticks() && end_events==1,"MIDI track duration/end");
            cursor=end;
        }
        check(trackcount==3 && note_on==31 && note_off==31,
              "MIDI track and note event counts");
        std::cout << "TESTS=PASS\n";
        std::cout << "NOTES=31 MELODY=15 BARS=4 FRAMES=352800\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "TESTS=FAIL " << e.what() << "\n";
        return 1;
    }
}
