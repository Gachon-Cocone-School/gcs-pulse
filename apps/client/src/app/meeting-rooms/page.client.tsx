'use client';

import { FormEvent, useCallback, useEffect, useMemo, useReducer } from 'react';
import Image from 'next/image';
import { Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/context/auth-context';
import { ApiError, meetingRoomsApi } from '@/lib/api';
import { toDateKey } from '@/lib/dateKeys';
import { hasPrivilegedRole } from '@/lib/types';
import type { MeetingRoom, MeetingRoomReservation } from '@/lib/types';

interface MeetingRoomsPageClientProps {
  dateParam?: string;
}

type TimePickerKey = 'start-hour' | 'start-minute' | 'end-hour' | 'end-minute';

interface FormState {
  startTime: string;
  endTime: string;
  purpose: string;
  formError: string | null;
  openPicker: TimePickerKey | null;
}

type FormAction =
  | { type: 'setStartTime'; value: string }
  | { type: 'setEndTime'; value: string }
  | { type: 'setPurpose'; value: string }
  | { type: 'setFormError'; value: string | null }
  | { type: 'setOpenPicker'; value: TimePickerKey | null };

interface PageState {
  selectedDate: string;
  rooms: MeetingRoom[];
  selectedRoomId: number | null;
  reservations: MeetingRoomReservation[];
  loadingState: {
    rooms: boolean;
    reservations: boolean;
  };
  submitting: boolean;
  cancelingId: number | null;
}

type PageAction =
  | { type: 'setSelectedDate'; value: string }
  | { type: 'setRooms'; value: MeetingRoom[] }
  | { type: 'setSelectedRoomId'; value: number | null }
  | { type: 'setReservations'; value: MeetingRoomReservation[] }
  | { type: 'setRoomsLoading'; value: boolean }
  | { type: 'setReservationsLoading'; value: boolean }
  | { type: 'setSubmitting'; value: boolean }
  | { type: 'setCancelingId'; value: number | null };

const INITIAL_FORM_STATE: FormState = {
  startTime: '09:00',
  endTime: '10:00',
  purpose: '',
  formError: null,
  openPicker: null,
};

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, index) => index);
const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, index) => index);

function formatTwoDigits(value: number): string {
  return String(value).padStart(2, '0');
}

function pageReducer(state: PageState, action: PageAction): PageState {
  switch (action.type) {
    case 'setSelectedDate':
      return { ...state, selectedDate: action.value };
    case 'setRooms':
      return { ...state, rooms: action.value };
    case 'setSelectedRoomId':
      return { ...state, selectedRoomId: action.value };
    case 'setReservations':
      return { ...state, reservations: action.value };
    case 'setRoomsLoading':
      if (state.loadingState.rooms === action.value) return state;
      return { ...state, loadingState: { ...state.loadingState, rooms: action.value } };
    case 'setReservationsLoading':
      if (state.loadingState.reservations === action.value) return state;
      return { ...state, loadingState: { ...state.loadingState, reservations: action.value } };
    case 'setSubmitting':
      return { ...state, submitting: action.value };
    case 'setCancelingId':
      return { ...state, cancelingId: action.value };
    default:
      return state;
  }
}

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case 'setStartTime':
      return { ...state, startTime: action.value };
    case 'setEndTime':
      return { ...state, endTime: action.value };
    case 'setPurpose':
      return { ...state, purpose: action.value };
    case 'setFormError':
      return { ...state, formError: action.value };
    case 'setOpenPicker':
      return { ...state, openPicker: action.value };
    default:
      return state;
  }
}

function toLocalDateTimeIso(dateKey: string, timeKey: string): string {
  const local = new Date(`${dateKey}T${timeKey}:00`);
  return local.toISOString();
}

function toMinutes(timeKey: string): number {
  const [hourText, minuteText] = timeKey.split(':');
  const hour = Number(hourText || 0);
  const minute = Number(minuteText || 0);
  return hour * 60 + minute;
}

function toTimeKey(totalMinutes: number): string {
  const normalized = Math.min(Math.max(totalMinutes, 0), 23 * 60 + 59);
  const hour = String(Math.floor(normalized / 60)).padStart(2, '0');
  const minute = String(normalized % 60).padStart(2, '0');
  return `${hour}:${minute}`;
}

function withOneHourAfter(startTime: string): string {
  return toTimeKey(toMinutes(startTime) + 60);
}

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(Math.max(value, min), max);
}

function splitTimeKey(timeKey: string): { hour: number; minute: number } {
  const [hourText, minuteText] = timeKey.split(':');
  return {
    hour: clamp(Number(hourText || 0), 0, 23),
    minute: clamp(Number(minuteText || 0), 0, 59),
  };
}

function mergeTimeKey(hour: number, minute: number): string {
  const hh = String(clamp(hour, 0, 23)).padStart(2, '0');
  const mm = String(clamp(minute, 0, 59)).padStart(2, '0');
  return `${hh}:${mm}`;
}

function formatTime(isoText: string): string {
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) return '-';
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

interface RoomSelectionCardProps {
  roomsLoading: boolean;
  rooms: MeetingRoom[];
  selectedRoomId: number | null;
  selectedRoom: MeetingRoom | null;
  onSelectRoom: (roomId: number | null) => void;
}

function RoomSelectionCard({ roomsLoading, rooms, selectedRoomId, selectedRoom, onSelectRoom }: RoomSelectionCardProps) {
  return (
    <Card className="glass-card rounded-xl border-[var(--sys-current-border)]">
      <CardHeader>
        <CardTitle className="text-base">회의실 선택</CardTitle>
        <CardDescription>
          {selectedRoom
            ? `${selectedRoom.name}${selectedRoom.location ? ` · ${selectedRoom.location}` : ''}`
            : '회의실을 선택하세요'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {roomsLoading ? (
          <div className="py-6 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
            <div className="space-y-4">
              <select
                className="w-full rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background px-3 py-2 text-sm text-foreground shadow-[var(--theme-control-shadow)] outline-none"
                value={selectedRoomId ?? ''}
                onChange={(e) => onSelectRoom(e.target.value ? Number(e.target.value) : null)}
                data-testid="meeting-room-select"
                aria-label="회의실 선택"
              >
                {rooms.length === 0 ? <option value="">회의실이 없습니다</option> : null}
                {rooms.map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.name}
                    {room.location ? ` · ${room.location}` : ''}
                  </option>
                ))}
              </select>

              {selectedRoom ? (
                <div className="space-y-2 rounded-lg border border-[var(--sys-current-border)] bg-muted/20 p-3 text-sm">
                  <p className="font-semibold text-foreground">{selectedRoom.name}</p>
                  <p className="text-muted-foreground">위치: {selectedRoom.location || '정보 없음'}</p>
                  <p className="text-muted-foreground whitespace-pre-wrap">설명: {selectedRoom.description || '설명 없음'}</p>
                </div>
              ) : null}
            </div>

            {selectedRoom?.image_url ? (
              <div className="overflow-hidden rounded-lg bg-muted/20">
                <div className="relative aspect-video w-full">
                  <Image
                    src={selectedRoom.image_url}
                    alt={`${selectedRoom.name} 이미지`}
                    fill
                    className="object-contain"
                    sizes="(min-width: 1024px) 40vw, 100vw"
                    unoptimized
                  />
                </div>
              </div>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ReservationsCardProps {
  selectedRoom: MeetingRoom | null;
  selectedDate: string;
  reservationsLoading: boolean;
  reservations: MeetingRoomReservation[];
  cancelingId: number | null;
  onCancelReservation: (reservationId: number) => void;
}

function ReservationsCard({
  selectedRoom,
  selectedDate,
  reservationsLoading,
  reservations,
  cancelingId,
  onCancelReservation,
}: ReservationsCardProps) {
  return (
    <Card className="glass-card rounded-xl border-[var(--sys-current-border)]">
      <CardHeader>
        <CardTitle className="text-base">예약 현황</CardTitle>
        <CardDescription>{selectedRoom ? `${selectedRoom.name} · ${selectedDate}` : '회의실을 먼저 선택하세요'}</CardDescription>
      </CardHeader>
      <CardContent>
        {reservationsLoading ? (
          <div className="py-10 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <Table
            data-testid="meeting-room-reservations-table"
            className="[&_thead_tr]:border-[var(--sys-current-border)] [&_tbody_tr]:border-[var(--sys-current-border)]"
          >
            <TableHeader>
              <TableRow>
                <TableHead>시간</TableHead>
                <TableHead>목적</TableHead>
                <TableHead>예약자</TableHead>
                <TableHead className="text-right">작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reservations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    예약이 없습니다.
                  </TableCell>
                </TableRow>
              ) : (
                reservations.map((reservation) => (
                  <TableRow key={reservation.id} data-testid={`meeting-room-reservation-row-${reservation.id}`}>
                    <TableCell>
                      {formatTime(reservation.start_at)} - {formatTime(reservation.end_at)}
                    </TableCell>
                    <TableCell>{reservation.purpose || '-'}</TableCell>
                    <TableCell>{reservation.reserved_by_name || '-'}</TableCell>
                    <TableCell className="text-right">
                      {reservation.can_cancel ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={cancelingId === reservation.id}
                          onClick={() => void onCancelReservation(reservation.id)}
                          data-testid={`meeting-room-cancel-${reservation.id}`}
                        >
                          {cancelingId === reservation.id ? '취소 중...' : '취소'}
                        </Button>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

interface ReservationCreateCardProps {
  selectedRoom: MeetingRoom | null;
  selectedDate: string;
  startTime: string;
  endTime: string;
  purpose: string;
  formError: string | null;
  openPicker: TimePickerKey | null;
  submitting: boolean;
  selectedRoomId: number | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onPurposeChange: (value: string) => void;
  onTogglePicker: (key: TimePickerKey) => void;
  onStartHourChange: (value: number) => void;
  onStartMinuteChange: (value: number) => void;
  onEndHourChange: (value: number) => void;
  onEndMinuteChange: (value: number) => void;
}

function ReservationCreateCard({
  selectedRoom,
  selectedDate,
  startTime,
  endTime,
  purpose,
  formError,
  openPicker,
  submitting,
  selectedRoomId,
  onSubmit,
  onPurposeChange,
  onTogglePicker,
  onStartHourChange,
  onStartMinuteChange,
  onEndHourChange,
  onEndMinuteChange,
}: ReservationCreateCardProps) {
  const { hour: startHour, minute: startMinute } = splitTimeKey(startTime);
  const { hour: endHour, minute: endMinute } = splitTimeKey(endTime);

  return (
    <Card className="glass-card rounded-xl border-[var(--sys-current-border)]">
      <CardHeader>
        <CardTitle className="text-base">예약 생성</CardTitle>
        <CardDescription>{selectedRoom ? `${selectedRoom.name} · ${selectedDate}` : '회의실을 먼저 선택하세요'}</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={onSubmit} data-testid="meeting-room-create-form">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="meeting-room-start-hour-trigger" className="text-sm text-muted-foreground">
                시작 시간
              </label>
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                <button
                  type="button"
                  id="meeting-room-start-hour-trigger"
                  onClick={() => onTogglePicker('start-hour')}
                  className="w-full rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background px-3 py-2 text-sm text-foreground text-left shadow-[var(--theme-control-shadow)]"
                  aria-label="시작 시 선택"
                  data-testid="meeting-room-start-hour-trigger"
                >
                  {formatTwoDigits(startHour)}
                </button>
                <span className="text-muted-foreground">:</span>
                <button
                  type="button"
                  onClick={() => onTogglePicker('start-minute')}
                  className="w-full rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background px-3 py-2 text-sm text-foreground text-left shadow-[var(--theme-control-shadow)]"
                  aria-label="시작 분 선택"
                  data-testid="meeting-room-start-minute-trigger"
                >
                  {formatTwoDigits(startMinute)}
                </button>
              </div>
              {openPicker === 'start-hour' ? (
                <div className="h-40 overflow-y-auto rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background">
                  {HOUR_OPTIONS.map((hour) => (
                    <button
                      key={hour}
                      type="button"
                      onClick={() => onStartHourChange(hour)}
                      className={`w-full px-3 py-2 text-left text-sm ${
                        hour === startHour ? 'bg-primary/15 text-primary font-medium' : 'text-foreground hover:bg-muted/40'
                      }`}
                    >
                      {formatTwoDigits(hour)}
                    </button>
                  ))}
                </div>
              ) : null}
              {openPicker === 'start-minute' ? (
                <div className="h-40 overflow-y-auto rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background">
                  {MINUTE_OPTIONS.map((minute) => (
                    <button
                      key={minute}
                      type="button"
                      onClick={() => onStartMinuteChange(minute)}
                      className={`w-full px-3 py-2 text-left text-sm ${
                        minute === startMinute ? 'bg-primary/15 text-primary font-medium' : 'text-foreground hover:bg-muted/40'
                      }`}
                    >
                      {formatTwoDigits(minute)}
                    </button>
                  ))}
                </div>
              ) : null}
              <input type="hidden" value={startTime} data-testid="meeting-room-start-input" readOnly />
            </div>

            <div className="space-y-2">
              <label htmlFor="meeting-room-end-hour-trigger" className="text-sm text-muted-foreground">
                종료 시간
              </label>
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                <button
                  type="button"
                  id="meeting-room-end-hour-trigger"
                  onClick={() => onTogglePicker('end-hour')}
                  className="w-full rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background px-3 py-2 text-sm text-foreground text-left shadow-[var(--theme-control-shadow)]"
                  aria-label="종료 시 선택"
                  data-testid="meeting-room-end-hour-trigger"
                >
                  {formatTwoDigits(endHour)}
                </button>
                <span className="text-muted-foreground">:</span>
                <button
                  type="button"
                  onClick={() => onTogglePicker('end-minute')}
                  className="w-full rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background px-3 py-2 text-sm text-foreground text-left shadow-[var(--theme-control-shadow)]"
                  aria-label="종료 분 선택"
                  data-testid="meeting-room-end-minute-trigger"
                >
                  {formatTwoDigits(endMinute)}
                </button>
              </div>
              {openPicker === 'end-hour' ? (
                <div className="h-40 overflow-y-auto rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background">
                  {HOUR_OPTIONS.map((hour) => (
                    <button
                      key={hour}
                      type="button"
                      onClick={() => onEndHourChange(hour)}
                      className={`w-full px-3 py-2 text-left text-sm ${
                        hour === endHour ? 'bg-primary/15 text-primary font-medium' : 'text-foreground hover:bg-muted/40'
                      }`}
                    >
                      {formatTwoDigits(hour)}
                    </button>
                  ))}
                </div>
              ) : null}
              {openPicker === 'end-minute' ? (
                <div className="h-40 overflow-y-auto rounded-[var(--theme-control-radius)] border border-[var(--sys-current-border)] bg-input-background">
                  {MINUTE_OPTIONS.map((minute) => (
                    <button
                      key={minute}
                      type="button"
                      onClick={() => onEndMinuteChange(minute)}
                      className={`w-full px-3 py-2 text-left text-sm ${
                        minute === endMinute ? 'bg-primary/15 text-primary font-medium' : 'text-foreground hover:bg-muted/40'
                      }`}
                    >
                      {formatTwoDigits(minute)}
                    </button>
                  ))}
                </div>
              ) : null}
              <input type="hidden" value={endTime} data-testid="meeting-room-end-input" readOnly />
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="reservation-purpose" className="text-sm text-muted-foreground">
              목적
            </label>
            <Textarea
              id="reservation-purpose"
              value={purpose}
              onChange={(e) => onPurposeChange(e.target.value)}
              placeholder="회의 목적을 입력하세요 (선택)"
              data-testid="meeting-room-purpose-input"
              className="border-[var(--sys-current-border)] bg-background text-foreground placeholder:text-muted-foreground"
            />
          </div>

          {formError ? (
            <Alert variant="destructive" data-testid="meeting-room-create-error">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Button
            type="submit"
            disabled={submitting || !selectedRoomId || !startTime || !endTime || toMinutes(startTime) >= toMinutes(endTime)}
            data-testid="meeting-room-create-submit"
          >
            {submitting ? '예약 중...' : '예약하기'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function MeetingRoomsPageClient({ dateParam }: MeetingRoomsPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);

  const initialDate = useMemo(() => {
    if (!dateParam) return toDateKey(new Date());
    return /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : toDateKey(new Date());
  }, [dateParam]);

  const [pageState, dispatchPage] = useReducer(pageReducer, {
    selectedDate: initialDate,
    rooms: [],
    selectedRoomId: null,
    reservations: [],
    loadingState: {
      rooms: false,
      reservations: false,
    },
    submitting: false,
    cancelingId: null,
  });
  const [formState, dispatchForm] = useReducer(formReducer, INITIAL_FORM_STATE);

  const { selectedDate, rooms, selectedRoomId, reservations, loadingState, submitting, cancelingId } = pageState;

  const selectedRoom = useMemo(
    () => rooms.find((room) => room.id === selectedRoomId) ?? null,
    [rooms, selectedRoomId],
  );

  const loadRooms = useCallback(async () => {
    dispatchPage({ type: 'setRoomsLoading', value: true });
    try {
      const list = await meetingRoomsApi.listRooms();
      dispatchPage({ type: 'setRooms', value: list });
      if (!selectedRoomId) {
        dispatchPage({ type: 'setSelectedRoomId', value: list[0]?.id ?? null });
      }
    } catch (error) {
      console.error(error);
      dispatchPage({ type: 'setRooms', value: [] });
      dispatchPage({ type: 'setSelectedRoomId', value: null });
    } finally {
      dispatchPage({ type: 'setRoomsLoading', value: false });
    }
  }, [selectedRoomId]);

  const loadReservations = useCallback(async () => {
    if (!selectedRoomId) {
      dispatchPage({ type: 'setReservations', value: [] });
      return;
    }

    dispatchPage({ type: 'setReservationsLoading', value: true });
    try {
      const list = await meetingRoomsApi.listReservations(selectedRoomId, selectedDate);
      dispatchPage({ type: 'setReservations', value: list });
    } catch (error) {
      console.error(error);
      dispatchPage({ type: 'setReservations', value: [] });
    } finally {
      dispatchPage({ type: 'setReservationsLoading', value: false });
    }
  }, [selectedRoomId, selectedDate]);

  useEffect(() => {
    if (!isAuthenticated || !hasAccess) return;
    void loadRooms();
  }, [isAuthenticated, hasAccess, loadRooms]);

  useEffect(() => {
    if (!isAuthenticated || !hasAccess || !selectedRoomId) return;
    void loadReservations();
  }, [isAuthenticated, hasAccess, selectedRoomId, selectedDate, loadReservations]);

  const { hour: startHour, minute: startMinute } = splitTimeKey(formState.startTime);
  const { hour: endHour, minute: endMinute } = splitTimeKey(formState.endTime);

  const handleStartHourChange = (nextHour: number) => {
    const nextStartTime = mergeTimeKey(nextHour, startMinute);
    dispatchForm({ type: 'setStartTime', value: nextStartTime });
    if (toMinutes(nextStartTime) >= toMinutes(formState.endTime)) {
      dispatchForm({ type: 'setEndTime', value: withOneHourAfter(nextStartTime) });
    }
    dispatchForm({ type: 'setOpenPicker', value: null });
  };

  const handleStartMinuteChange = (nextMinute: number) => {
    const nextStartTime = mergeTimeKey(startHour, nextMinute);
    dispatchForm({ type: 'setStartTime', value: nextStartTime });
    if (toMinutes(nextStartTime) >= toMinutes(formState.endTime)) {
      dispatchForm({ type: 'setEndTime', value: withOneHourAfter(nextStartTime) });
    }
    dispatchForm({ type: 'setOpenPicker', value: null });
  };

  const handleEndHourChange = (nextHour: number) => {
    dispatchForm({ type: 'setEndTime', value: mergeTimeKey(nextHour, endMinute) });
    dispatchForm({ type: 'setOpenPicker', value: null });
  };

  const handleEndMinuteChange = (nextMinute: number) => {
    dispatchForm({ type: 'setEndTime', value: mergeTimeKey(endHour, nextMinute) });
    dispatchForm({ type: 'setOpenPicker', value: null });
  };

  const handleTogglePicker = (key: TimePickerKey) => {
    dispatchForm({ type: 'setOpenPicker', value: formState.openPicker === key ? null : key });
  };

  const handleCreateReservation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedRoomId) return;
    if (!formState.startTime || !formState.endTime || toMinutes(formState.startTime) >= toMinutes(formState.endTime)) return;

    dispatchForm({ type: 'setFormError', value: null });
    dispatchPage({ type: 'setSubmitting', value: true });
    try {
      await meetingRoomsApi.createReservation(selectedRoomId, {
        start_at: toLocalDateTimeIso(selectedDate, formState.startTime),
        end_at: toLocalDateTimeIso(selectedDate, formState.endTime),
        purpose: formState.purpose.trim() || undefined,
      });
      dispatchForm({ type: 'setPurpose', value: '' });
      await loadReservations();
    } catch (error) {
      if (error instanceof ApiError) {
        dispatchForm({ type: 'setFormError', value: error.message });
      } else {
        console.error(error);
        dispatchForm({ type: 'setFormError', value: '예약 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.' });
      }
    } finally {
      dispatchPage({ type: 'setSubmitting', value: false });
    }
  };

  const handleCancelReservation = async (reservationId: number) => {
    dispatchPage({ type: 'setCancelingId', value: reservationId });
    try {
      await meetingRoomsApi.cancelReservation(reservationId);
      await loadReservations();
    } catch (error) {
      console.error(error);
    } finally {
      dispatchPage({ type: 'setCancelingId', value: null });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!hasAccess) {
    return <AccessDeniedView reason="student-only" />;
  }

  return (
    <div className="min-h-screen bg-background bg-mesh">
      <Navigation />
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <PageHeader
          title="회의실 예약"
          description="약속된 시간은 소중하게, 뒷사람을 위한 여유는 넉넉하게"
          actions={
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => dispatchPage({ type: 'setSelectedDate', value: e.target.value })}
              className="w-[180px]"
              data-testid="meeting-room-date-input"
              aria-label="예약 날짜"
            />
          }
        />

        <RoomSelectionCard
          roomsLoading={loadingState.rooms}
          rooms={rooms}
          selectedRoomId={selectedRoomId}
          selectedRoom={selectedRoom}
          onSelectRoom={(value) => dispatchPage({ type: 'setSelectedRoomId', value })}
        />

        <ReservationsCard
          selectedRoom={selectedRoom}
          selectedDate={selectedDate}
          reservationsLoading={loadingState.reservations}
          reservations={reservations}
          cancelingId={cancelingId}
          onCancelReservation={handleCancelReservation}
        />

        <ReservationCreateCard
          selectedRoom={selectedRoom}
          selectedDate={selectedDate}
          startTime={formState.startTime}
          endTime={formState.endTime}
          purpose={formState.purpose}
          formError={formState.formError}
          openPicker={formState.openPicker}
          submitting={submitting}
          selectedRoomId={selectedRoomId}
          onSubmit={handleCreateReservation}
          onPurposeChange={(value) => dispatchForm({ type: 'setPurpose', value })}
          onTogglePicker={handleTogglePicker}
          onStartHourChange={handleStartHourChange}
          onStartMinuteChange={handleStartMinuteChange}
          onEndHourChange={handleEndHourChange}
          onEndMinuteChange={handleEndMinuteChange}
        />
      </main>
    </div>
  );
}
