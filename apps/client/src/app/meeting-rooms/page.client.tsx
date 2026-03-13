'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Navigation } from '@/components/Navigation';
import { PageHeader } from '@/components/PageHeader';
import { AccessDeniedView } from '@/components/views/AccessDenied';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/context/auth-context';
import { meetingRoomsApi } from '@/lib/api';
import { toDateKey } from '@/lib/dateKeys';
import { hasPrivilegedRole } from '@/lib/types';
import type { MeetingRoom, MeetingRoomReservation } from '@/lib/types';

interface MeetingRoomsPageClientProps {
  dateParam?: string;
}


function toLocalDateTimeIso(dateKey: string, timeKey: string): string {
  const local = new Date(`${dateKey}T${timeKey}:00`);
  return local.toISOString();
}

function formatTime(isoText: string): string {
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export default function MeetingRoomsPageClient({ dateParam }: MeetingRoomsPageClientProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const hasAccess = hasPrivilegedRole(user?.roles);

  const initialDate = useMemo(() => {
    if (!dateParam) return toDateKey(new Date());
    return /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : toDateKey(new Date());
  }, [dateParam]);

  const [selectedDate, setSelectedDate] = useState<string>(initialDate);
  const [rooms, setRooms] = useState<MeetingRoom[]>([]);
  const [selectedRoomId, setSelectedRoomId] = useState<number | null>(null);
  const [reservations, setReservations] = useState<MeetingRoomReservation[]>([]);

  const [roomsLoading, setRoomsLoading] = useState<boolean>(false);
  const [reservationsLoading, setReservationsLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [cancelingId, setCancelingId] = useState<number | null>(null);

  const [startTime, setStartTime] = useState<string>('09:00');
  const [endTime, setEndTime] = useState<string>('10:00');
  const [purpose, setPurpose] = useState<string>('');


  const selectedRoom = useMemo(
    () => rooms.find((room) => room.id === selectedRoomId) ?? null,
    [rooms, selectedRoomId],
  );

  const loadRooms = useCallback(async () => {
    setRoomsLoading(true);
    try {
      const list = await meetingRoomsApi.listRooms();
      setRooms(list);
      setSelectedRoomId((prev) => prev ?? list[0]?.id ?? null);
    } catch (error) {
      console.error(error);
      setRooms([]);
      setSelectedRoomId(null);
    } finally {
      setRoomsLoading(false);
    }
  }, []);

  const loadReservations = useCallback(async () => {
    if (!selectedRoomId) {
      setReservations([]);
      return;
    }

    setReservationsLoading(true);
    try {
      const list = await meetingRoomsApi.listReservations(selectedRoomId, selectedDate);
      setReservations(list);
    } catch (error) {
      console.error(error);
      setReservations([]);
    } finally {
      setReservationsLoading(false);
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

  const handleCreateReservation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedRoomId) return;
    if (!startTime || !endTime || startTime >= endTime) return;

    setSubmitting(true);
    try {
      await meetingRoomsApi.createReservation(selectedRoomId, {
        start_at: toLocalDateTimeIso(selectedDate, startTime),
        end_at: toLocalDateTimeIso(selectedDate, endTime),
        purpose: purpose.trim() || undefined,
      });
      setPurpose('');
      await loadReservations();
    } catch (error) {
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelReservation = async (reservationId: number) => {
    setCancelingId(reservationId);
    try {
      await meetingRoomsApi.cancelReservation(reservationId);
      await loadReservations();
    } catch (error) {
      console.error(error);
    } finally {
      setCancelingId(null);
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
          description="gcs/교수/admin 사용자를 위한 회의실 예약 페이지"
          actions={
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-[180px]"
              data-testid="meeting-room-date-input"
              aria-label="예약 날짜"
            />
          }
        />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {roomsLoading ? (
            <Card className="glass-card rounded-xl md:col-span-2 lg:col-span-3">
              <CardContent className="py-10 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </CardContent>
            </Card>
          ) : (
            rooms.map((room) => {
              const isSelected = room.id === selectedRoomId;
              return (
                <Card
                  key={room.id}
                  className={`glass-card rounded-xl cursor-pointer transition-colors ${
                    isSelected ? 'border-[var(--sys-current-border)] bg-[var(--sys-current-bg)]/30' : ''
                  }`}
                  data-testid={`meeting-room-card-${room.id}`}
                  onClick={() => setSelectedRoomId(room.id)}
                >
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between gap-2">
                      <span>{room.name}</span>
                      {isSelected ? <Badge variant="secondary">선택됨</Badge> : null}
                    </CardTitle>
                    <CardDescription>{room.location || '위치 정보 없음'}</CardDescription>
                  </CardHeader>
                  {room.description ? (
                    <CardContent>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">{room.description}</p>
                    </CardContent>
                  ) : null}
                </Card>
              );
            })
          )}
        </div>

        <Card className="glass-card rounded-xl">
          <CardHeader>
            <CardTitle className="text-base">예약 생성</CardTitle>
            <CardDescription>
              {selectedRoom ? `${selectedRoom.name} · ${selectedDate}` : '회의실을 먼저 선택하세요'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCreateReservation} data-testid="meeting-room-create-form">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label htmlFor="reservation-start" className="text-sm text-muted-foreground">
                    시작 시간
                  </label>
                  <Input
                    id="reservation-start"
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    data-testid="meeting-room-start-input"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="reservation-end" className="text-sm text-muted-foreground">
                    종료 시간
                  </label>
                  <Input
                    id="reservation-end"
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    data-testid="meeting-room-end-input"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label htmlFor="reservation-purpose" className="text-sm text-muted-foreground">
                  목적
                </label>
                <Textarea
                  id="reservation-purpose"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="회의 목적을 입력하세요 (선택)"
                  data-testid="meeting-room-purpose-input"
                />
              </div>

              <Button
                type="submit"
                disabled={submitting || !selectedRoomId || !startTime || !endTime || startTime >= endTime}
                data-testid="meeting-room-create-submit"
              >
                {submitting ? '예약 중...' : '예약하기'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="glass-card rounded-xl">
          <CardHeader>
            <CardTitle className="text-base">예약 현황</CardTitle>
            <CardDescription>
              {selectedRoom ? `${selectedRoom.name} · ${selectedDate}` : '회의실을 먼저 선택하세요'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {reservationsLoading ? (
              <div className="py-10 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : (
              <Table data-testid="meeting-room-reservations-table">
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
                    reservations.map((reservation) => {
                      return (
                        <TableRow
                          key={reservation.id}
                          data-testid={`meeting-room-reservation-row-${reservation.id}`}
                        >
                          <TableCell>
                            {formatTime(reservation.start_at)} - {formatTime(reservation.end_at)}
                          </TableCell>
                          <TableCell>{reservation.purpose || '-'}</TableCell>
                          <TableCell>{reservation.reserved_by_user_id}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={cancelingId === reservation.id}
                              onClick={() => void handleCancelReservation(reservation.id)}
                              data-testid={`meeting-room-cancel-${reservation.id}`}
                            >
                              {cancelingId === reservation.id ? '취소 중...' : '취소'}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
