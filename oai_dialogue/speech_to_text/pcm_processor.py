from typing import List, Optional
import numpy as np
import scipy


class PcmProcessor:
    BYTES_PER_SAMPLE = 2
    def __init__(self, sample_rate: int, channel_cnt:int, frames_per_chunk:int = 0, millis_per_chunk:int = 0):
        self.sample_rate = sample_rate
        self.channel_cnt = channel_cnt
        self.frames_per_chunk = frames_per_chunk
        if frames_per_chunk and millis_per_chunk:
            print(self.__class__.__name__, ": frames_per_chunk overrides millis_per_chunk. Max one of them should be assigned.")
        elif millis_per_chunk:
            self.frames_per_chunk = int(millis_per_chunk * sample_rate / 1000.0)
        self._incomplete_chunk_frames:Optional[np.ndarray] = None 
        self._incomplete_frame_bytes = bytearray()

    def get_frames(self, channel_cnt:int, pcm16bytes:bytes) -> np.ndarray:
        bytes_per_incoming_frame = self.BYTES_PER_SAMPLE * channel_cnt
        if self._incomplete_frame_bytes:
            pcm16bytes = bytes(self._incomplete_frame_bytes) + pcm16bytes
            self._incomplete_frame_bytes.clear()
        
        if rem := len(pcm16bytes) % bytes_per_incoming_frame:
            self._incomplete_frame_bytes.extend(pcm16bytes[-rem:])
            pcm16bytes = pcm16bytes[:-rem]
        
        incoming_frame_cnt = len(pcm16bytes) // bytes_per_incoming_frame
        if incoming_frame_cnt == 0:
            return []
        return np.frombuffer(pcm16bytes, dtype="<i2").reshape(-1, channel_cnt)
    
    def get_frame_chunks_from_bytes(self, sample_rate:int, channel_cnt:int, pcm16bytes:bytes) -> List[np.ndarray]:
        frames = self.get_frames(channel_cnt, pcm16bytes)
        return self.get_frame_chunks(sample_rate, channel_cnt, frames)
    
    def get_frame_chunks(self, sample_rate:int, channel_cnt:int, frames:np.ndarray) -> List[np.ndarray]:

        need_chunking = self.frames_per_chunk not in (0, len(frames)) or self._incomplete_chunk_frames is not None
        if self.sample_rate == sample_rate and self.channel_cnt == channel_cnt and not need_chunking:
            return [frames] if frames.size else []
        if sample_rate != self.sample_rate or channel_cnt != self.channel_cnt:
            frames = frames.astype(np.float32)
            if channel_cnt != self.channel_cnt:
                if self.channel_cnt == 1:
                    frames = frames.mean(axis=1)
                    if frames.ndim == 1:
                        frames = frames[:, None]                 
                else:
                    raise(Exception("Only remixing to mono supported"))
            if sample_rate != self.sample_rate:
                g = np.gcd(sample_rate, self.sample_rate)
                up, down = self.sample_rate // g, sample_rate // g
                frames = np.clip(scipy.signal.resample_poly(frames, up, down), -32768, 32767)
            frames = frames.astype(np.int16)
        
        if need_chunking:
            if self._incomplete_chunk_frames is not None:
                frames = np.concatenate((self._incomplete_chunk_frames, frames))
                self._incomplete_chunk_frames = None

            frame_cnt = frames.shape[0]
            fpc = self.frames_per_chunk
            chunkable_frame_cnt = (frame_cnt // fpc) * fpc
            chunkable_frames = frames[:chunkable_frame_cnt]
            self._incomplete_chunk_frames = frames[chunkable_frame_cnt:] if chunkable_frame_cnt < frame_cnt else None

            if chunkable_frame_cnt > 0:
                # reshape to (num_chunks, spc, channels) then flatten last two dims
                chunk_cnt = chunkable_frame_cnt // fpc
                y = chunkable_frames.reshape(chunk_cnt, fpc, self.channel_cnt)
                return [y[i].reshape(-1) for i in range(chunk_cnt)]
            return []
        return [frames]

    def get_chunks(self, sample_rate:int, channel_cnt:int, pcm16bytes:bytes) -> List[bytes]:
        return [frame_chunk.tobytes() for frame_chunk in self.get_frame_chunks_from_bytes(sample_rate, channel_cnt, pcm16bytes)]


