// Petite Victoire -- experimental native Carbon 32-bit front end for Darling.
// This file requires a genuine Carbon/CoreAudio i386 SDK and has NOT been
// compiled in the Linux-only qualification environment.
// The audio callback itself is allocation-free and never uses IPC directly.

#include <Carbon/Carbon.h>
#include <CoreAudio/AudioHardware.h>

#include "music.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <vector>

namespace {

constexpr int kW = 960;
constexpr int kH = 730;
constexpr int kStartX = 76;
constexpr int kEndX = 920;
constexpr int kGridTop = 279;
constexpr int kGridBottom = 499;
constexpr int kGridMin = 60;
constexpr int kGridMax = 81;
constexpr int kPixelsPerSemitone = 10;

struct App {
    pv::Song song;
    std::vector<float> pcm;
    pv::Playback player;
    WindowRef window = nullptr;
    EventLoopTimerRef timer = nullptr;
    AudioDeviceID device = 0;
    AudioDeviceIOProcID proc = nullptr;
    bool device_active = false;
    std::string status = "Carbon i386 - prototype non qualifie";
    App() : song(pv::demo_song()), pcm(pv::synthesize(song)), player(pcm) {}
};
App app;

Rect rect(short left, short top, short right, short bottom) {
    Rect r; SetRect(&r, left, top, right, bottom); return r;
}
void fill_rect(short x, short y, short w, short h) {
    const Rect r=rect(x,y,x+w,y+h); PaintRect(&r);
}
void invalid_all() {
    if (app.window) { const Rect r=rect(0,0,kW,kH); InvalWindowRect(app.window,&r); }
}
void color(unsigned short r, unsigned short g, unsigned short b) {
    const RGBColor c = {r, g, b}; RGBForeColor(&c);
}
void text(int x, int y, const std::string& s) {
    MoveTo(static_cast<short>(x), static_cast<short>(y));
    const size_t limit = std::min<size_t>(s.size(), 320);
    DrawText(s.data(), 0, static_cast<short>(limit));
}
void draw_button(int x, int y, int w, const char* name, bool on = false) {
    const Rect r = rect(x, y, x+w, y+38);
    color(on ? 0xA800 : 0xEEEE, on ? 0xD600 : 0xEEEE,
          on ? 0xF900 : 0xEEEE);
    PaintRect(&r);
    color(0x5555,0x7777,0x9999); FrameRect(&r);
    color(0x1111,0x2222,0x3333); TextSize(13); text(x+12,y+25,name);
}

int diatonic_step(int pitch) {
    static const int degrees[12] = {0,0,1,1,2,3,3,4,4,5,5,6};
    return (pitch/12 - 1)*7 + degrees[pitch%12];
}
int score_y(int pitch) {
    // Treble staff's bottom line is E4 (MIDI 64).
    return 185 - (diatonic_step(pitch)-diatonic_step(64))*6;
}
int note_x(int tick, int total) {
    return kStartX + (kEndX-kStartX)*tick/total;
}
void draw_score() {
    TextSize(17); color(0x1111,0x2222,0x3333);
    text(35, 52, "Petite Victoire   |   Partition et piano roll synchronises");
    TextSize(12); text(37, 79, "Cle de SOL   4/4   Do majeur   120 BPM");
    for (int y : {137,149,161,173,185}) {
        color(0x5555,0x5555,0x5555);
        MoveTo(kStartX,y); LineTo(kEndX,y);
    }
    TextSize(30); color(0x1111,0x1111,0x1111);
    text(46, 175, "G");  // G-clef marker, no font glyph assumption
    for (int bar=0; bar <= app.song.bars; ++bar) {
        const int x = note_x(bar * 4 * pv::kTicksPerQuarter, app.song.total_ticks());
        MoveTo(x,137); LineTo(x,185);
        TextSize(10); text(x+3,205,std::to_string(bar+1));
    }
    for (const auto& n : app.song.notes) {
        if (!n.melody) continue;
        const int x = note_x(n.start, app.song.total_ticks())+9;
        const int y = score_y(n.pitch);
        const bool half_note = n.duration >= 2 * pv::kTicksPerQuarter;
        const Rect head = rect(x-6,y-4,x+7,y+5);
        color(0x1111,0x1111,0x1111);
        if (half_note) FrameOval(&head); else PaintOval(&head);
        if (y >= 160) { MoveTo(x+6,y); LineTo(x+6,y-32); }
        else { MoveTo(x-6,y); LineTo(x-6,y+32); }
        if (n.duration == pv::kTicksPerQuarter/2) {
            if (y >= 160) { MoveTo(x+6,y-32); LineTo(x+19,y-18); }
            else { MoveTo(x-6,y+32); LineTo(x+7,y+43); }
        }
        if (n.pitch == 60 || n.pitch == 81) {
            MoveTo(x-10,y); LineTo(x+10,y); // ledger line
        }
        TextSize(10);
        color(0x1800,0x5700,0x9000);
        text(x-8,107,pv::solfege(n.pitch));
    }
}

void draw_roll() {
    TextSize(13); color(0x2222,0x3333,0x4444);
    text(35,263,"PIANO ROLL  |  cliquer pour ajouter / supprimer une note (pas : croche)");
    for (int pitch=kGridMin; pitch <= kGridMax; ++pitch) {
        const int y = kGridTop + (kGridMax-pitch)*kPixelsPerSemitone;
        const bool black = (pitch%12==1 || pitch%12==3 || pitch%12==6 || pitch%12==8 || pitch%12==10);
        const Rect row = rect(38,y,kEndX,y+10);
        color(black ? 0xE500 : 0xFFFF, black ? 0xE900 : 0xFFFF, black ? 0xEE00 : 0xFFFF);
        PaintRect(&row);
        color(0xDDDD,0xDDDD,0xDDDD);
        MoveTo(38,y); LineTo(kEndX,y);
        if (pitch%12==0) {
            color(0x3333,0x3333,0x3333); TextSize(10);
            text(40,y+9,pv::solfege(pitch)+std::to_string(pitch/12-1));
        }
    }
    for (int t=0; t<=app.song.total_ticks(); t+=pv::kTicksPerQuarter/2) {
        const int x=note_x(t,app.song.total_ticks());
        const bool bar = t%(pv::kTicksPerQuarter*4)==0;
        color(bar?0x8888:0xDDDD,bar?0x8888:0xDDDD,bar?0x8888:0xDDDD);
        MoveTo(x,kGridTop); LineTo(x,kGridBottom);
    }
    for (const auto& n : app.song.notes) {
        if (n.pitch<kGridMin || n.pitch>kGridMax) continue;
        const int x=note_x(n.start,app.song.total_ticks());
        const int x2=note_x(n.start+n.duration,app.song.total_ticks());
        const int y=kGridTop+(kGridMax-n.pitch)*kPixelsPerSemitone;
        const Rect r=rect(x+1,y+1,std::max(x+3,x2-1),y+9);
        if (n.melody) color(0x2400,0x8800,0xBE00);
        else color(0x9900,0xB200,0xC800);
        PaintRect(&r);
    }
    if (app.player.playing() && !app.pcm.empty()) {
        const int x = kStartX + static_cast<int>((kEndX-kStartX)*
            (app.player.position()%app.pcm.size())/app.pcm.size());
        color(0xF400,0x3300,0x2200);
        MoveTo(x,kGridTop); LineTo(x,kGridBottom);
    }
}

void draw_controls() {
    draw_button(75,529,100,"PLAY",app.player.playing());
    draw_button(185,529,100,"STOP");
    draw_button(295,529,120,app.player.looping()?"LOOP ON":"LOOP OFF",app.player.looping());
    draw_button(75,588,150,"EXPORT MIDI");
    draw_button(238,588,150,"EXPORT WAV");

    color(0x2222,0x2222,0x2222); TextSize(13);
    text(454,540,"VOLUME");
    text(706,540,"PANORAMIQUE");
    const Rect vol = rect(454,550,654,557);
    color(0xCCCC,0xCCCC,0xCCCC); PaintRect(&vol);
    const int vx=454+static_cast<int>(200*app.player.volume());
    color(0x3500,0x8200,0xA600); fill_rect(static_cast<short>(vx-4),544,8,21);
    const Rect pan=rect(706,550,906,557);
    color(0xCCCC,0xCCCC,0xCCCC); PaintRect(&pan);
    const int px=806+static_cast<int>(100*app.player.pan());
    color(0x3500,0x8200,0xA600); fill_rect(static_cast<short>(px-4),544,8,21);
    TextSize(11); color(0x3333,0x3333,0x3333);
    text(454,580,std::to_string(static_cast<int>(app.player.volume()*100))+"%");
    text(704,580,"L       C       R");
    text(75,667,"Exports uniquement sur clic, dans D4WR_PV_OUTPUT_DIR (dossier existant).");
    text(75,693,app.status);
}

void redraw() {
    if (!app.window) return;
    SetPortWindowPort(app.window);
    const Rect area=rect(0,0,kW,kH);
    color(0xFFFF,0xFFFF,0xFFFF); PaintRect(&area);
    draw_score(); draw_roll(); draw_controls();
}

OSStatus audio_callback(AudioDeviceID, const AudioTimeStamp*, const AudioBufferList*,
                        const AudioTimeStamp*, AudioBufferList* out,
                        const AudioTimeStamp*, void*) {
    if (!out || out->mNumberBuffers != 1 || out->mBuffers[0].mNumberChannels != 2 ||
        !out->mBuffers[0].mData || out->mBuffers[0].mDataByteSize % (2*sizeof(float)) != 0)
        return -1;
    app.player.render(static_cast<float*>(out->mBuffers[0].mData),
                      out->mBuffers[0].mDataByteSize/(2*sizeof(float)));
    return noErr;
}

void stop_audio() {
    app.player.stop();
    if (app.device_active && app.proc) {
        AudioDeviceStop(app.device,app.proc);
        app.device_active=false;
    }
}

void play_audio() {
    if (!app.proc) {
        AudioObjectPropertyAddress addr = {
            kAudioHardwarePropertyDefaultOutputDevice,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMaster
        };
        UInt32 size=sizeof(app.device);
        if (AudioObjectGetPropertyData(kAudioObjectSystemObject,&addr,0,nullptr,&size,&app.device)!=noErr ||
            !app.device) {
            app.status="CoreAudio : peripherique de sortie indisponible";
            return;
        }
        if (AudioDeviceCreateIOProcID(app.device,audio_callback,nullptr,&app.proc)!=noErr || !app.proc) {
            app.status="CoreAudio : impossible de creer IOProc";
            return;
        }
    }
    if (app.device_active) stop_audio();
    app.player.play();
    if (AudioDeviceStart(app.device,app.proc)!=noErr) {
        app.player.stop(); app.status="CoreAudio : AudioDeviceStart a echoue";
    } else {
        app.device_active=true;
        app.status="Lecture via CoreAudio i386";
    }
}

bool existing_file(const std::string& path) {
    struct stat st; return ::stat(path.c_str(),&st)==0;
}
void export_click(bool is_midi) {
    const char* directory=std::getenv("D4WR_PV_OUTPUT_DIR");
    struct stat st;
    if (!directory || !*directory || ::stat(directory,&st)!=0 || !S_ISDIR(st.st_mode)) {
        app.status="Export bloque : definir D4WR_PV_OUTPUT_DIR (dossier existant)";
        return;
    }
    const std::string filename=std::string(directory) +
        (is_midi?"/Petite-Victoire.mid":"/Petite-Victoire.wav");
    if (existing_file(filename)) {
        app.status="Export bloque : fichier existant (aucun ecrasement)";
        return;
    }
    const bool ok=is_midi ? pv::export_midi(filename,app.song)
                          : pv::export_wav(filename,app.pcm);
    app.status=ok ? "Export OK : "+filename : "Export echoue";
}

void edit_note(Point where) {
    const int x=std::max(kStartX,std::min(kEndX-1,static_cast<int>(where.h)));
    const int pitch=kGridMax-(where.v-kGridTop)/kPixelsPerSemitone;
    const int tick=(x-kStartX)*app.song.total_ticks()/(kEndX-kStartX);
    const int snapped=(tick/(pv::kTicksPerQuarter/2))*(pv::kTicksPerQuarter/2);
    stop_audio(); // waveform and editor are never concurrently mutated
    pv::toggle_note(app.song,pitch,snapped,pv::kTicksPerQuarter/2);
    app.pcm=pv::synthesize(app.song);
    app.player.set_pcm(app.pcm);
    app.status="Note modifiee : "+pv::solfege(pitch)+" (MIDI)";
}

void on_click(Point point) {
    const int x=point.h, y=point.v;
    if (y>=529 && y<=567) {
        if (x>=75 && x<175) play_audio();
        else if (x>=185 && x<285) { stop_audio(); app.status="Arret"; }
        else if (x>=295 && x<415) app.player.set_loop(!app.player.looping());
    } else if (y>=588 && y<=626) {
        if (x>=75 && x<225) export_click(true);
        else if (x>=238 && x<388) export_click(false);
    } else if (y>=534 && y<=575) {
        if (x>=450 && x<=660) app.player.set_volume((x-454)/200.0f);
        if (x>=702 && x<=910) app.player.set_pan((x-806)/100.0f);
    } else if (x>=kStartX && x<kEndX && y>=kGridTop && y<kGridBottom) {
        edit_note(point);
    }
    invalid_all();
}

pascal OSStatus window_handler(EventHandlerCallRef,EventRef event,void*) {
    const UInt32 cls=GetEventClass(event), kind=GetEventKind(event);
    if (cls==kEventClassWindow && kind==kEventWindowDrawContent) {
        redraw(); return noErr;
    }
    if (cls==kEventClassMouse && kind==kEventMouseDown) {
        Point position={0,0};
        if (GetEventParameter(event,kEventParamMouseLocation,typeQDPoint,nullptr,
                              sizeof(position),nullptr,&position)==noErr) {
            SetPortWindowPort(app.window);
            GlobalToLocal(&position);
            on_click(position);
        }
        return noErr;
    }
    if (cls==kEventClassWindow && kind==kEventWindowClose) {
        stop_audio();
        if (app.proc) AudioDeviceDestroyIOProcID(app.device,app.proc);
        app.proc=nullptr;
        QuitApplicationEventLoop();
        return noErr;
    }
    return eventNotHandledErr;
}

pascal void timer_callback(EventLoopTimerRef,void*) {
    if (app.device_active && !app.player.playing() && !app.player.looping()) {
        stop_audio();
    }
    if (app.window && app.device_active)
        invalid_all();
}

} // namespace

int main() {
    const Rect bounds=rect(70,55,70+kW,55+kH);
    const OSStatus result=CreateNewWindow(kDocumentWindowClass,
        kWindowStandardDocumentAttributes,&bounds,&app.window);
    if (result!=noErr || !app.window) {
        std::fprintf(stderr,"PV_CARBON_WINDOW_CREATE_FAIL=%d\n",(int)result);
        return 10;
    }
    SetWindowTitleWithCFString(app.window,CFSTR("Petite Victoire - D4Wrling i386"));
    const EventTypeSpec types[]={
        {kEventClassWindow,kEventWindowDrawContent},
        {kEventClassWindow,kEventWindowClose},
        {kEventClassMouse,kEventMouseDown}
    };
    const EventHandlerUPP handler=NewEventHandlerUPP(window_handler);
    InstallWindowEventHandler(app.window,handler,3,types,nullptr,nullptr);
    const EventLoopTimerUPP timer=NewEventLoopTimerUPP(timer_callback);
    InstallEventLoopTimer(GetMainEventLoop(),0,kEventDurationSecond/25,
                          timer,nullptr,&app.timer);
    ShowWindow(app.window);
    invalid_all();
    RunApplicationEventLoop();
    if (app.timer) RemoveEventLoopTimer(app.timer);
    DisposeEventLoopTimerUPP(timer);
    DisposeEventHandlerUPP(handler);
    return 0;
}
