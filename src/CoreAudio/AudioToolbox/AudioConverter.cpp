/*
This file is part of Darling.

Copyright (C) 2020 Lubos Dolezel

Darling is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Darling is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "AudioConverter.h"
#include "AudioConverterImpl.h"
#include <CarbonCore/MacErrors.h>
#include <stdexcept>
#include <cstring>
#include <algorithm>

OSStatus AudioConverterNew(const AudioStreamBasicDescription* inSourceFormat, const AudioStreamBasicDescription* inDestinationFormat, AudioConverterRef* outAudioConverter)
{
	return AudioConverter::create(inSourceFormat, inDestinationFormat, (AudioConverter**)outAudioConverter);
}

OSStatus AudioConverterNewSpecific(const AudioStreamBasicDescription* inSourceFormat, const AudioStreamBasicDescription* inDestinationFormat, UInt32 inNumberClassDescriptions, const AudioClassDescription* nClassDescriptions, AudioConverterRef* outAudioConverter)
{
	// FIXME
	return AudioConverterNew(inSourceFormat, inDestinationFormat, outAudioConverter);
}

OSStatus AudioConverterReset(AudioConverterRef inAudioConverter)
{
	if (inAudioConverter)
	{
		((AudioConverter*)inAudioConverter)->flush();
		return noErr;
	}
	else
		return paramErr;
}

OSStatus AudioConverterDispose(AudioConverterRef inAudioConverter)
{
	delete (AudioConverter*)inAudioConverter;
	return noErr;
}

OSStatus AudioConverterGetProperty(AudioConverterRef inAudioConverter, AudioConverterPropertyID inPropertyID, UInt32 *ioPropertyDataSize, void *outPropertyData)
{
	return ((AudioConverter*)inAudioConverter)->getProperty(inPropertyID, ioPropertyDataSize, outPropertyData);
}

OSStatus AudioConverterGetPropertyInfo(AudioConverterRef inAudioConverter, AudioConverterPropertyID inPropertyID, UInt32 *outSize, Boolean *outWritable)
{
	return ((AudioConverter*)inAudioConverter)->getPropertyInfo(inPropertyID, outSize, outWritable);
}

OSStatus AudioConverterSetProperty(AudioConverterRef inAudioConverter, AudioConverterPropertyID inPropertyID, UInt32 inPropertyDataSize, const void *inPropertyData)
{
	return ((AudioConverter*)inAudioConverter)->setProperty(inPropertyID, inPropertyDataSize, inPropertyData);
}

namespace
{
// AudioConverterConvertBuffer and AudioConverterConvertComplexBuffer only handle conversions
// where each input frame gives exactly one output frame: linear PCM on both sides, one frame
// per packet, the same sample rate, interleaved samples (the converter takes and gives a
// single buffer). The public contract says that they fail otherwise, sample rate conversions
// and compressed formats included: those go through AudioConverterFillComplexBuffer.
bool isFixedRatioPCM(const AudioStreamBasicDescription& format)
{
	if (format.mFormatID != kAudioFormatLinearPCM || format.mFramesPerPacket != 1 || !format.mBytesPerFrame)
		return false;
	if ((format.mFormatFlags & kAudioFormatFlagIsNonInterleaved) && format.mChannelsPerFrame > 1)
		return false;
	// The converter reads and writes packed samples only: padded frames would be misread
	return format.mBitsPerChannel % 8 == 0 && format.mBytesPerPacket == format.mBytesPerFrame
		&& format.mBytesPerFrame == format.mBitsPerChannel / 8 * format.mChannelsPerFrame;
}

OSStatus checkFixedRatioPCM(const AudioConverter* converter)
{
	const AudioStreamBasicDescription& source = converter->sourceFormat();
	const AudioStreamBasicDescription& destination = converter->destinationFormat();

	if (!isFixedRatioPCM(source) || !isFixedRatioPCM(destination) || source.mSampleRate != destination.mSampleRate)
		return kAudioConverterErr_FormatNotSupported;
	return noErr;
}

// The whole input of AudioConverterConvertComplexBuffer, handed to the converter in the
// pieces it asks for, then an empty answer for the end of the stream.
struct ComplexBufferInput
{
	const uint8_t* data;
	UInt32 bytesPerFrame;
	UInt32 channels;
	UInt32 frames;
	UInt32 position;
};

OSStatus complexBufferInputProc(AudioConverterRef, UInt32* ioNumberDataPackets, AudioBufferList* ioData,
	AudioStreamPacketDescription** outDataPacketDescription, void* userData)
{
	ComplexBufferInput* input = static_cast<ComplexBufferInput*>(userData);
	const UInt32 frames = std::min(*ioNumberDataPackets, input->frames - input->position);

	if (outDataPacketDescription)
		*outDataPacketDescription = nullptr;
	if (ioData->mNumberBuffers < 1)
		return kAudio_ParamError;

	ioData->mBuffers[0].mNumberChannels = input->channels;
	ioData->mBuffers[0].mData = frames ? const_cast<uint8_t*>(input->data) + size_t(input->position) * input->bytesPerFrame : nullptr;
	ioData->mBuffers[0].mDataByteSize = frames * input->bytesPerFrame;

	input->position += frames;
	*ioNumberDataPackets = frames;
	return noErr;
}
}

OSStatus AudioConverterConvertBuffer(AudioConverterRef inAudioConverter, UInt32 inInputDataSize, const void* inInputData, UInt32 *ioOutputDataSize, void *outOutputData)
{
	if (!inAudioConverter || !ioOutputDataSize || (inInputDataSize && !inInputData) || (*ioOutputDataSize && !outOutputData))
		return kAudio_ParamError;

	AudioConverter* converter = reinterpret_cast<AudioConverter*>(inAudioConverter);
	OSStatus status = checkFixedRatioPCM(converter);
	if (status != noErr)
		return status;

	const AudioStreamBasicDescription& source = converter->sourceFormat();
	const AudioStreamBasicDescription& destination = converter->destinationFormat();
	if (inInputDataSize % source.mBytesPerFrame)
		return kAudioConverterErr_InvalidInputSize;

	AudioBufferList in, out;
	in.mNumberBuffers = out.mNumberBuffers = 1;
	in.mBuffers[0].mNumberChannels = source.mChannelsPerFrame;
	out.mBuffers[0].mNumberChannels = destination.mChannelsPerFrame;

	in.mBuffers[0].mDataByteSize = inInputDataSize;
	in.mBuffers[0].mData = const_cast<void*>(inInputData);

	out.mBuffers[0].mDataByteSize = *ioOutputDataSize;
	out.mBuffers[0].mData = outOutputData;

	status = AudioConverterConvertComplexBuffer(inAudioConverter, inInputDataSize / source.mBytesPerFrame, &in, &out);
	*ioOutputDataSize = out.mBuffers[0].mDataByteSize;

	return status;
}

OSStatus AudioConverterFillComplexBuffer(AudioConverterRef inAudioConverter, AudioConverterComplexInputDataProc inInputDataProc, void *inInputDataProcUserData, UInt32 *ioOutputDataPacketSize, AudioBufferList *outOutputData, AudioStreamPacketDescription* outPacketDescription)
{
	return ((AudioConverter*)inAudioConverter)->fillComplex(inInputDataProc, inInputDataProcUserData, ioOutputDataPacketSize, outOutputData, outPacketDescription);
}

OSStatus AudioConverterConvertComplexBuffer(AudioConverterRef inAudioConverter, UInt32 inNumberPCMFrames, const AudioBufferList *inInputData, AudioBufferList *outOutputData)
{
	if (!inAudioConverter || !inInputData || !outOutputData)
		return kAudio_ParamError;

	AudioConverter* converter = reinterpret_cast<AudioConverter*>(inAudioConverter);
	OSStatus status = checkFixedRatioPCM(converter);
	if (status != noErr)
		return status;

	// Interleaved formats only: exactly one buffer on each side
	if (inInputData->mNumberBuffers != 1 || outOutputData->mNumberBuffers != 1)
		return kAudio_ParamError;

	const AudioStreamBasicDescription& source = converter->sourceFormat();
	const AudioStreamBasicDescription& destination = converter->destinationFormat();
	const AudioBuffer& inBuffer = inInputData->mBuffers[0];
	AudioBuffer& outBuffer = outOutputData->mBuffers[0];
	const uint64_t inBytes = uint64_t(inNumberPCMFrames) * source.mBytesPerFrame;
	const uint64_t outBytes = uint64_t(inNumberPCMFrames) * destination.mBytesPerFrame;

	if (inBuffer.mDataByteSize < inBytes)
		return kAudioConverterErr_InvalidInputSize;
	if (inBytes && !inBuffer.mData)
		return kAudio_ParamError;

	// All of the input has to fit: nothing is converted rather than a part of it,
	// since the caller could not tell which input frames were left out
	if (outBuffer.mDataByteSize < outBytes)
	{
		outBuffer.mDataByteSize = 0;
		return kAudioConverterErr_InvalidOutputSize;
	}
	if (outBytes && !outBuffer.mData)
		return kAudio_ParamError;

	if (!inNumberPCMFrames)
	{
		outBuffer.mDataByteSize = 0;
		return noErr;
	}

	ComplexBufferInput input = { static_cast<const uint8_t*>(inBuffer.mData), source.mBytesPerFrame,
		source.mChannelsPerFrame, inNumberPCMFrames, 0 };
	UInt32 outputFrames = inNumberPCMFrames;
	outBuffer.mDataByteSize = UInt32(outBytes);

	status = AudioConverterFillComplexBuffer(inAudioConverter, complexBufferInputProc, &input, &outputFrames, outOutputData, nullptr);

	// Each call converts a self-contained buffer: nothing may carry over to the next one
	converter->flush();

	// Never report success for a conversion that lost frames on the way
	if (status == noErr && (outputFrames != inNumberPCMFrames || outBuffer.mDataByteSize != outBytes || input.position != inNumberPCMFrames))
		status = kAudioConverterErr_UnspecifiedError;

	// The refusals above leave the output buffer untouched. An error during the conversion
	// reports no output at all, but the buffer may already hold part of it
	if (status != noErr)
		outBuffer.mDataByteSize = 0;
	return status;
}
