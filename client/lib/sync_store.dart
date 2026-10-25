import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class SyncStore {
  static const apiBaseUrl = String.fromEnvironment('OMNI_API_BASE_URL', defaultValue: 'https://www.udn4f.com');
  static const websocketBaseUrl = 'wss://www.udn4f.com';
  final String baseUrl; final String token;
  final Map<String, dynamic> projects = {}; dynamic cursor;
  WebSocketChannel? socket;
  SyncStore(this.baseUrl, this.token);

  Future<void> rehydrate() async {
    final r = await http.get(Uri.parse('$baseUrl/v1/sync/export?since=$cursor'), headers: {'Authorization':'Bearer $token'});
    if (r.statusCode != 200) throw Exception('sync failed: ${r.body}');
    final body = jsonDecode(r.body) as Map<String,dynamic>;
    final manifest = body['manifest'] as Map<String,dynamic>;
    final next = <String,dynamic>{ for (final p in (manifest['projects'] as List)) p['id'] as String: p };
    projects..clear()..addAll(next); cursor = manifest['cursor'] as int;
    socket = WebSocketChannel.connect(Uri.parse('$websocketBaseUrl/v1/ws?token=$token'));
  }
  Stream<Map<String,dynamic>> get events => socket!.stream.map((e)=>jsonDecode(e as String) as Map<String,dynamic>);
  void dispose() => socket?.sink.close();
}
